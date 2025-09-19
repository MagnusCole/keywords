import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _slugify(text: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower()).strip()
    t = re.sub(r"\s+", "_", t)
    return t or "cluster"


@dataclass
class ClusterResult:
    cluster_id: int
    label: str
    keywords: list[dict[str, Any]]


class SemanticClusterer:
    """Embeddings-based semantic clusterer with graceful fallback.

    - Tries to use sentence-transformers + scikit-learn.
    - If unavailable or fails, returns None to signal fallback to heuristic clustering.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        use_hdbscan: bool = False,
        random_state: int = 42,
    ) -> None:
        self.model_name = model_name
        self.use_hdbscan = use_hdbscan
        self.random_state = random_state
        self._model = None
        self._imports_ready = False
        # Simple disk cache for embeddings
        self._cache_dir = Path("cache")
        self._cache_dir.mkdir(exist_ok=True)
        safe_model = model_name.replace("/", "_")
        self._cache_file = self._cache_dir / f"emb_{safe_model}.json"
        self._emb_cache: dict[str, list[float]] = self._load_cache()

        try:
            # Lazy import to avoid hard dependency
            from sentence_transformers import SentenceTransformer  # type: ignore
            from sklearn.cluster import KMeans  # type: ignore
            from sklearn.metrics import silhouette_score  # type: ignore

            self.SentenceTransformer = SentenceTransformer
            self.KMeans = KMeans
            self.silhouette_score = silhouette_score
            self._imports_ready = True

            # HDBSCAN optional
            self.HDBSCAN = None
            if use_hdbscan:
                try:
                    from hdbscan import HDBSCAN  # type: ignore

                    self.HDBSCAN = HDBSCAN
                except Exception:
                    logging.warning("HDBSCAN not available; falling back to KMeans")
        except Exception:
            logging.warning(
                "sentence-transformers or scikit-learn not available; semantic clustering disabled"
            )

    def _load_model(self) -> None:
        if self._model is None and self._imports_ready:
            try:
                self._model = self.SentenceTransformer(self.model_name)
            except Exception as e:
                logging.warning(f"Failed to load embedding model '{self.model_name}': {e}")

    def _load_cache(self) -> dict:
        try:
            if self._cache_file.exists():
                return json.loads(self._cache_file.read_text(encoding="utf-8"))
        except Exception as e:
            logging.warning(f"Failed to load embedding cache: {e}")
        return {}

    def _save_cache(self) -> None:
        try:
            self._cache_file.write_text(json.dumps(self._emb_cache), encoding="utf-8")
        except Exception as e:
            logging.warning(f"Failed to save embedding cache: {e}")

    def _choose_k(self, embeddings) -> int:
        # Simple heuristic for K
        n = len(embeddings)
        if n <= 2:
            return 1
        max_k = max(2, min(10, n - 1))
        best_k, best_score = 2, -1.0
        for k in range(2, max_k + 1):
            try:
                km = self.KMeans(n_clusters=k, random_state=self.random_state)
                labels = km.fit_predict(embeddings)
                if len(set(labels)) <= 1:
                    continue
                score = self.silhouette_score(embeddings, labels)
                if score > best_score:
                    best_k, best_score = k, score
            except Exception as e:
                logging.debug(f"KMeans silhouette scoring failed for k={k}: {e}")
                continue
        return best_k

    @staticmethod
    def _top_ngram_label(keywords: list[str], n: int = 2, top_k: int = 2) -> str:
        tokens = []
        for kw in keywords:
            w = re.findall(r"[a-zA-Záéíóúñü]+", kw.lower())
            tokens.append(w)

        grams: Counter[str] = Counter()
        for w in tokens:
            for i in range(len(w) - n + 1):
                grams[" ".join(w[i : i + n])] += 1

        if not grams:
            # fallback to most common single words
            words = Counter([w for t in tokens for w in t])
            label = " ".join([w for w, _ in words.most_common(top_k)])
            return label or "cluster"

        label = " ".join([w for w, _ in grams.most_common(top_k)])
        return label

    def fit_transform(self, items: list[dict[str, Any]]) -> list[ClusterResult] | None:
        """Assigns cluster_id and label to items; returns cluster groups or None if unavailable."""
        if not self._imports_ready or not items:
            return None

        self._load_model()
        if self._model is None:
            return None

        texts = [it.get("keyword", "") for it in items]
        try:
            # Use cache where available
            missing_indices = []
            embeddings = []
            for idx, txt in enumerate(texts):
                vec = self._emb_cache.get(txt)
                if vec is None:
                    missing_indices.append(idx)
                    embeddings.append(None)  # placeholder
                else:
                    embeddings.append(vec)

            if missing_indices:
                to_encode = [texts[i] for i in missing_indices]
                new_vecs = self._model.encode(to_encode, show_progress_bar=False)
                for i, vec in zip(missing_indices, new_vecs, strict=False):
                    v = [float(x) for x in (vec.tolist() if hasattr(vec, "tolist") else vec)]
                    embeddings[i] = v
                    self._emb_cache[texts[i]] = v
                self._save_cache()

            # Ensure embeddings is a plain list of lists
            import numpy as np  # type: ignore

            embeddings = np.array(embeddings)

            # Choose clustering algorithm
            if self.use_hdbscan and self.HDBSCAN is not None:
                clusterer = self.HDBSCAN(min_cluster_size=max(2, len(texts) // 20))
                labels = clusterer.fit_predict(embeddings)
                # HDBSCAN can assign -1 as noise; map noise to its own cluster
                noise_map = {}
                next_id = 0
                mapped: list[int] = []
                for lb in labels:
                    if lb not in noise_map:
                        noise_map[lb] = next_id
                        next_id += 1
                    mapped.append(noise_map[lb])
                labels = mapped
            else:
                k = self._choose_k(embeddings)
                km = self.KMeans(n_clusters=k, random_state=self.random_state)
                labels = km.fit_predict(embeddings)

            # Group by labels
            groups: dict[int, list[dict[str, Any]]] = {}
            for it, lb in zip(items, labels, strict=False):
                groups.setdefault(int(lb), []).append(it)

            # Build cluster results with labels
            results: list[ClusterResult] = []
            for cid, members in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
                member_texts = [m.get("keyword", "") for m in members]
                label = self._top_ngram_label(member_texts)
                results.append(ClusterResult(cluster_id=int(cid), label=label, keywords=members))

            return results
        except Exception as e:
            logging.warning(f"Semantic clustering failed, using heuristic fallback: {e}")
            return None
