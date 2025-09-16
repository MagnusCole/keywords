import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pipeline_config import PRODUCTION_CLUSTERING_CONFIG, StandardClusteringConfig


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
        model_name: str | None = None,
        use_hdbscan: bool | None = None,
        random_state: int | None = None,
        cache_dir: str = "cache",
        config: StandardClusteringConfig | None = None,
    ) -> None:
        """Initialize with production-standardized configuration."""
        # Use production config as default
        self.config = config or PRODUCTION_CLUSTERING_CONFIG
        
        # Override with explicit parameters if provided
        self.model_name = model_name or self.config.EMBEDDING_MODEL
        self.use_hdbscan = use_hdbscan if use_hdbscan is not None else True  # Try HDBSCAN first
        self.random_state = random_state or self.config.KMEANS_RANDOM_STATE
        
        self._model = None
        self._imports_ready = False

        # Configurable cache directory
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(exist_ok=True)
        safe_model = self.model_name.replace("/", "_").replace("\\", "_")
        self._cache_file = self._cache_dir / f"emb_{safe_model}.json"
        self._emb_cache: dict[str, list[float]] = self._load_cache()

        logging.info(f"SemanticClusterer initialized with standardized config v{self.config.VERSION}")
        logging.info(f"Model: {self.model_name}, HDBSCAN: {self.use_hdbscan}, Random state: {self.random_state}")

        try:
            # Lazy import to avoid hard dependency
            from sentence_transformers import SentenceTransformer
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score

            self.SentenceTransformer = SentenceTransformer
            self.KMeans = KMeans
            self.silhouette_score = silhouette_score
            self._imports_ready = True

            # HDBSCAN optional
            self.HDBSCAN = None
            if use_hdbscan:
                try:
                    from hdbscan import HDBSCAN

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
        """Load embeddings cache from disk with better error handling."""
        try:
            if self._cache_file.exists():
                cache_data = json.loads(self._cache_file.read_text(encoding="utf-8"))
                if isinstance(cache_data, dict):
                    logging.info(
                        f"Loaded {len(cache_data)} cached embeddings from {self._cache_file}"
                    )
                    return cache_data
                else:
                    logging.warning(f"Invalid cache format in {self._cache_file}, expected dict")
        except Exception as e:
            logging.warning(f"Failed to load embedding cache from {self._cache_file}: {e}")
        return {}

    def _save_cache(self) -> None:
        """Save embeddings cache to disk with better error handling."""
        try:
            self._cache_file.write_text(
                json.dumps(self._emb_cache, separators=(",", ":")), encoding="utf-8"
            )
            logging.debug(f"Saved {len(self._emb_cache)} embeddings to cache")
        except Exception as e:
            logging.warning(f"Failed to save embedding cache to {self._cache_file}: {e}")

    def _choose_k(self, embeddings, min_k: int | None = None, max_k: int | None = None) -> int:
        """Choose optimal K for KMeans using standardized configuration and silhouette score."""
        n = len(embeddings)
        if n <= 2:
            return 1

        # Use standardized configuration
        min_k = min_k or self.config.KMEANS_MIN_CLUSTERS
        if max_k is None:
            max_k = max(min_k, int(n * self.config.KMEANS_MAX_CLUSTERS_RATIO))
        max_k = min(max_k, n - 1)

        if min_k >= max_k:
            return max_k

        best_k, best_score = min_k, self.config.SILHOUETTE_MIN_SCORE

        for k in range(min_k, max_k + 1):
            try:
                km = self.KMeans(
                    n_clusters=k, 
                    random_state=self.config.KMEANS_RANDOM_STATE,
                    n_init=self.config.KMEANS_N_INIT,
                    max_iter=self.config.KMEANS_MAX_ITER
                )
                labels = km.fit_predict(embeddings)

                # Skip if all items in same cluster or too few clusters
                unique_labels = len(set(labels))
                if unique_labels <= 1:
                    continue

                score = self.silhouette_score(embeddings, labels)
                logging.debug(f"KMeans k={k}: silhouette={score:.3f}, clusters={unique_labels}")

                if score > best_score:
                    best_k, best_score = k, score

            except Exception as e:
                logging.debug(f"KMeans silhouette scoring failed for k={k}: {e}")
                continue

        logging.info(f"Selected optimal k={best_k} with silhouette score {best_score:.3f} (using standardized config)")
        return best_k

    def _determine_cluster_count(
        self, keywords: list[str], target_clusters: int | None = None
    ) -> int:
        """Determine optimal cluster count based on priority rules."""
        n_keywords = len(keywords)

        # Priority 1: Explicit override parameter
        if target_clusters is not None:
            logging.info(f"Using explicit target_clusters={target_clusters}")
            return max(1, min(target_clusters, n_keywords))

        # Priority 2: Config setting (would need to pass from main)
        # For now, use dynamic estimation

        # Priority 3: Dynamic estimation based on data size
        if n_keywords <= 3:
            return 1
        elif n_keywords <= 10:
            return min(3, n_keywords - 1)
        elif n_keywords <= 50:
            return min(5, n_keywords // 3)
        else:
            # Scale with square root for large datasets
            estimated = int(n_keywords**0.5)
            return max(3, min(15, estimated))  # Guardrails: 3-15 clusters

    def _safe_silhouette_score(self, embeddings, labels) -> float | None:
        """Calculate silhouette score with error handling."""
        try:
            unique_labels = len(set(labels))
            if unique_labels <= 1 or unique_labels >= len(embeddings):
                return None
            return float(self.silhouette_score(embeddings, labels))
        except Exception as e:
            logging.debug(f"Silhouette score calculation failed: {e}")
            return None

    def _group_by_labels(self, keywords: list[str], labels) -> dict[str, list[str]]:
        """Group keywords by cluster labels."""
        groups: dict[int, list[str]] = {}
        for keyword, label in zip(keywords, labels, strict=False):
            groups.setdefault(int(label), []).append(keyword)

        # Convert to string keys sorted by cluster size
        result = {}
        for i, (_, members) in enumerate(sorted(groups.items(), key=lambda x: (-len(x[1]), x[0]))):
            result[f"cluster_{i}"] = members

        return result

    def _try_hdbscan(
        self, embeddings, min_samples: int | None = None
    ) -> tuple[list[int] | None, dict]:
        """Try HDBSCAN clustering with quality assessment."""
        if not self.use_hdbscan or self.HDBSCAN is None:
            return None, {"reason": "HDBSCAN not enabled or unavailable"}

        try:
            n = len(embeddings)
            min_cluster_size = max(2, n // 20)  # Minimum 2, scale with data size
            if min_samples is None:
                min_samples = max(1, min_cluster_size // 2)

            clusterer = self.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                cluster_selection_epsilon=0.1,
            )
            labels = clusterer.fit_predict(embeddings)

            # Analyze results
            unique_labels = set(labels)
            noise_count = sum(1 for label in labels if label == -1)
            cluster_count = len(unique_labels) - (1 if -1 in unique_labels else 0)

            stats = {
                "algorithm": "HDBSCAN",
                "cluster_count": cluster_count,
                "noise_count": noise_count,
                "noise_ratio": noise_count / len(labels),
                "min_cluster_size": min_cluster_size,
                "min_samples": min_samples,
            }

            # Quality checks
            if cluster_count < 2:
                return None, {**stats, "reason": "Too few clusters generated"}

            if noise_count / len(labels) > 0.5:
                return None, {**stats, "reason": "Too many noise points"}

            logging.info(f"HDBSCAN succeeded: {cluster_count} clusters, {noise_count} noise points")

            # Map noise points to separate clusters
            labels_mapped = []
            noise_counter = cluster_count
            for label in labels:
                if label == -1:
                    labels_mapped.append(noise_counter)
                    noise_counter += 1
                else:
                    labels_mapped.append(label)

            return labels_mapped, stats

        except Exception as e:
            return None, {"reason": f"HDBSCAN failed: {e}"}

    def _generate_tfidf_label(self, keywords: list[str], max_features: int = 3) -> str:
        """Generate cluster label using simple term frequency to find representative terms."""
        if not keywords:
            return "empty_cluster"

        if len(keywords) == 1:
            # Single keyword: use first 2-3 words
            words = keywords[0].split()[:max_features]
            return " ".join(words)

        try:
            # Simple term frequency approach instead of full TF-IDF
            import re
            from collections import Counter

            # Extract all words from keywords
            all_words = []
            for kw in keywords:
                # Clean and split keywords
                words = re.findall(r"\b[a-zA-Z]{2,}\b", kw.lower())
                all_words.extend(words)

            # Count word frequencies
            word_counts = Counter(all_words)

            # Filter out common stop words manually
            stop_words = {
                "the",
                "and",
                "for",
                "with",
                "from",
                "are",
                "you",
                "all",
                "any",
                "can",
                "had",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "its",
                "may",
                "new",
                "now",
                "old",
                "see",
                "two",
                "who",
                "boy",
                "did",
                "she",
                "use",
                "way",
                "too",
                "but",
                "not",
            }

            # Get most frequent words excluding stop words
            filtered_words = [
                (word, count)
                for word, count in word_counts.most_common()
                if word not in stop_words and len(word) > 2
            ]

            # Take top N words
            top_words = [word for word, _ in filtered_words[:max_features]]

            if top_words:
                return " ".join(top_words)
            else:
                # Ultimate fallback to n-gram approach
                return self._top_ngram_label(keywords, n=2, top_k=max_features)

        except Exception as e:
            logging.debug(f"Term frequency labeling failed: {e}, using n-gram fallback")
            # Fallback to existing n-gram method
            return self._top_ngram_label(keywords, n=2, top_k=max_features)

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

    def fit_transform(
        self, items: list[dict[str, Any]]
    ) -> list[ClusterResult] | None:  # noqa: C901
        """
        Assigns cluster_id and label to items using standardized algorithm selection.

        Uses production configuration for algorithm priority and parameters.
        """
        if not self._imports_ready or not items:
            return None

        self._load_model()
        if self._model is None:
            return None

        texts = [it.get("keyword", "") for it in items]
        logging.info(f"Clustering {len(texts)} keywords with standardized algorithm selection v{self.config.VERSION}")

        try:
            # Use cache where available (if enabled)
            if self.config.EMBEDDING_CACHE_ENABLED:
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
            else:
                # No caching - encode all
                new_vecs = self._model.encode(texts, show_progress_bar=False)
                embeddings = [[float(x) for x in (vec.tolist() if hasattr(vec, "tolist") else vec)] for vec in new_vecs]

            # Ensure embeddings is a proper numpy array
            import numpy as np

            embeddings = np.array(embeddings)

            # Determine target cluster count
            target_clusters = self._determine_cluster_count(texts)

            # Use standardized algorithm priority
            labels, method_used, algorithm_stats = self._apply_clustering_algorithm(embeddings, target_clusters)

            # Group by labels
            groups: dict[int, list[dict[str, Any]]] = {}
            for it, lb in zip(items, labels, strict=False):
                groups.setdefault(int(lb), []).append(it)

            # Build cluster results with TF-IDF based labels
            results: list[ClusterResult] = []
            for cid, members in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
                member_texts = [m.get("keyword", "") for m in members]
                label = self._generate_tfidf_label(member_texts)
                results.append(ClusterResult(cluster_id=int(cid), label=label, keywords=members))

            # Log clustering summary with standardized config info
            silhouette = algorithm_stats.get('silhouette_score', 'N/A')
            logging.info(f"Clustering complete: {len(results)} clusters using {method_used}, silhouette={silhouette}")
            logging.info(f"Algorithm priority used: {list(self.config.ALGORITHM_PRIORITY)}")

            return results

        except Exception as e:
            logging.error(f"Clustering failed: {e}")
            return None

    def _apply_clustering_algorithm(self, embeddings, target_clusters: int) -> tuple[list[int], str, dict]:
        """Apply clustering using standardized algorithm priority."""
        for algorithm in self.config.ALGORITHM_PRIORITY:
            if algorithm == "hdbscan" and self.use_hdbscan:
                labels, stats = self._try_hdbscan_standardized(embeddings)
                if labels is not None:
                    return labels, "HDBSCAN", stats
                    
            elif algorithm == "kmeans":
                labels, stats = self._try_kmeans_standardized(embeddings, target_clusters)
                if labels is not None:
                    return labels, "KMeans", stats
                    
            elif algorithm == "manual":
                # Manual clustering fallback (single cluster)
                labels = [0] * len(embeddings)
                stats = {"method": "manual", "clusters": 1}
                return labels, "Manual", stats
        
        # Should never reach here due to manual fallback
        raise RuntimeError("All clustering algorithms failed")

    def _try_hdbscan_standardized(self, embeddings) -> tuple[list[int] | None, dict]:
        """Try HDBSCAN with standardized configuration."""
        try:
            if not hasattr(self, 'HDBSCAN') or self.HDBSCAN is None:
                return None, {"reason": "HDBSCAN not available"}
                
            clusterer = self.HDBSCAN(
                min_cluster_size=self.config.HDBSCAN_MIN_CLUSTER_SIZE,
                min_samples=self.config.HDBSCAN_MIN_SAMPLES,
                metric=self.config.HDBSCAN_METRIC
            )
            labels = clusterer.fit_predict(embeddings).tolist()
            
            # Validate quality
            unique_labels = len(set(labels))
            noise_count = labels.count(-1)
            
            if unique_labels <= 1 or noise_count / len(labels) > 0.5:
                return None, {"reason": "poor quality", "clusters": unique_labels, "noise_ratio": noise_count / len(labels)}
            
            silhouette = self.silhouette_score(embeddings, labels) if unique_labels > 1 else -1.0
            
            if silhouette < self.config.SILHOUETTE_MIN_SCORE:
                return None, {"reason": "low silhouette", "silhouette_score": silhouette}
            
            return labels, {"clusters": unique_labels, "silhouette_score": silhouette, "noise_count": noise_count}
            
        except Exception as e:
            return None, {"reason": f"error: {e}"}

    def _try_kmeans_standardized(self, embeddings, target_clusters: int) -> tuple[list[int] | None, dict]:
        """Try KMeans with standardized configuration."""
        try:
            optimal_k = self._choose_k(embeddings, max_k=target_clusters)
            
            km = self.KMeans(
                n_clusters=optimal_k,
                random_state=self.config.KMEANS_RANDOM_STATE,
                n_init=self.config.KMEANS_N_INIT,
                max_iter=self.config.KMEANS_MAX_ITER
            )
            labels = km.fit_predict(embeddings).tolist()
            
            # Calculate quality metrics
            silhouette = self.silhouette_score(embeddings, labels) if optimal_k > 1 else 0.0
            inertia = getattr(km, 'inertia_', 0.0)
            
            return labels, {
                "clusters": optimal_k,
                "silhouette_score": silhouette,
                "inertia": inertia,
                "iterations": getattr(km, 'n_iter_', 0)
            }
            
        except Exception as e:
            return None, {"reason": f"error: {e}"}
            silhouette = self._safe_silhouette_score(embeddings, labels)
            logging.info(
                f"Clustering complete: {len(results)} clusters using {method_used}, "
                f"silhouette={silhouette:.3f}"
                if silhouette
                else "silhouette=N/A"
            )

            return results

        except Exception as e:
            logging.warning(f"Semantic clustering failed, using heuristic fallback: {e}")
            return None
