#!/usr/bin/env python3
"""
Keyword Finder - Sistema automático de descubrimiento de keywords
Diseñado para AQXION
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

from reliability_report import generate_reliability_report
from src.ads_volume import GoogleAdsVolumeProvider
from src.categorization import KeywordCategorizer
from src.clustering import SemanticClusterer
from src.database import Keyword, KeywordDatabase
from src.exporters import KeywordExporter
from src.scoring import KeywordScorer
from src.scrapers import CompetitorScraper, GoogleScraper
from src.trends import TrendsAnalyzer

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError as _e:
    logging.debug(f"dotenv not loaded (module missing): {_e}")


class KeywordFinder:
    """Orquestador principal del sistema de keyword finding"""

    def __init__(self, config: dict | None = None):
        base = self._load_default_config()
        if config:
            base.update(config)
        self.config = base
        self._setup_logging()

        # Inicializar componentes
        self.db = KeywordDatabase(self.config["database_path"])
        self.scraper = GoogleScraper(
            delay_range=(self.config["request_delay_min"], self.config["request_delay_max"]),
            max_retries=self.config["max_retries"],
        )
        self.trends = TrendsAnalyzer(
            hl=self.config["google_trends_hl"], tz=self.config["google_trends_tz"]
        )
        self.scorer = KeywordScorer(
            trend_weight=self.config["trend_weight"],
            volume_weight=self.config["volume_weight"],
            competition_weight=self.config["competition_weight"],
        )
        self.exporter = KeywordExporter()
        self.clusterer = SemanticClusterer(use_hdbscan=self.config.get("use_hdbscan", False))
        self.ads_provider = GoogleAdsVolumeProvider()
        self.categorizer = KeywordCategorizer(
            target_geo=self.config["geo"], target_business="services"
        )

        logging.info("KeywordFinder initialized successfully")

    def _should_expand_more(self, current_raw_count: int) -> bool:
        """Check if we need to expand more keywords to reach target raw count"""
        target_raw = self.config.get("target_raw", 0)
        if target_raw <= 0:
            return False
        return current_raw_count < target_raw

    def _adjust_filtering_thresholds(self, keywords: list[dict]) -> tuple[float, float]:
        """Dynamically adjust filtering thresholds to hit target filtered count"""
        target_filtered = self.config.get("target_filtered", 0)
        if target_filtered <= 0:
            # No target, use configured defaults
            return self.config.get("min_score", 0.0), self.config.get("max_competition", 1.0)

        # Sort keywords by score (descending) to take the top N
        sorted_kw = sorted(keywords, key=lambda x: x.get("score", 0), reverse=True)
        
        if len(sorted_kw) <= target_filtered:
            # We have fewer keywords than target, use lenient thresholds
            return 0.0, 1.0
            
        # Take the target_filtered-th keyword's score as our minimum threshold
        threshold_keyword = sorted_kw[target_filtered - 1]
        min_score_dynamic = max(0.0, threshold_keyword.get("score", 0) - 5.0)  # Small buffer
        
        # For competition, find the max competition in our target set
        target_set = sorted_kw[:target_filtered]
        max_competition_dynamic = max([kw.get("competition", 0) for kw in target_set], default=1.0)
        max_competition_dynamic = min(1.0, max_competition_dynamic + 0.1)  # Small buffer
        
        logging.info(f"Volume targeting: adjusted thresholds to min_score={min_score_dynamic:.1f}, max_competition={max_competition_dynamic:.2f}")
        return min_score_dynamic, max_competition_dynamic

    def _diversify_seeds_for_clusters(self, current_seeds: list[str], current_clusters: int) -> list[str]:
        """Generate additional diverse seeds to reach target cluster count"""
        target_clusters = self.config.get("target_clusters", 0)
        if target_clusters <= 0 or current_clusters >= target_clusters:
            return current_seeds

        # Predefined seed diversification patterns for Spanish markets
        diversification_patterns = {
            "marketing": ["ventas", "negocios", "publicidad", "branding", "comunicacion", "redes sociales"],
            "ventas": ["marketing", "comercio", "negociacion", "clientes", "crm", "conversion"],
            "negocios": ["empresas", "startups", "emprendimiento", "estrategia", "consultoria", "servicios"],
            "curso": ["capacitacion", "entrenamiento", "seminario", "taller", "formacion", "educacion"],
            "digital": ["online", "tecnologia", "web", "internet", "software", "herramientas"],
            "consultoria": ["asesoria", "servicios", "profesional", "experto", "especialista", "coaching"],
        }

        new_seeds = list(current_seeds)
        seeds_to_add = max(1, (target_clusters - current_clusters) * 2)  # 2 seeds per missing cluster

        # Add diversification based on existing seeds
        for seed in current_seeds:
            if len(new_seeds) >= len(current_seeds) + seeds_to_add:
                break
            for pattern, variations in diversification_patterns.items():
                if pattern in seed.lower():
                    for var in variations:
                        if var not in new_seeds and len(new_seeds) < len(current_seeds) + seeds_to_add:
                            new_seeds.append(var)

        # Add generic high-value seeds if we still need more
        generic_seeds = [
            "servicios", "profesional", "herramientas", "solucion", "estrategia", 
            "consultoria", "experto", "especialista", "empresa", "comercial"
        ]
        for generic in generic_seeds:
            if generic not in new_seeds and len(new_seeds) < len(current_seeds) + seeds_to_add:
                new_seeds.append(generic)

        if len(new_seeds) > len(current_seeds):
            added_count = len(new_seeds) - len(current_seeds)
            logging.info(f"Volume targeting: added {added_count} diverse seeds to reach target clusters")

        return new_seeds

    def _print_volume_targeting_summary(self, total_raw: int, filtered_count: int, cluster_count: int):
        """Print volume targeting performance summary"""
        target_raw = self.config.get("target_raw", 0)
        target_filtered = self.config.get("target_filtered", 0)
        target_clusters = self.config.get("target_clusters", 0)
        
        print(f"\n🎯 Volume Targeting Summary:")
        print("-" * 50)
        
        if target_raw > 0:
            status = "✅" if total_raw >= target_raw else "⚠️"
            print(f"Raw Keywords:      {status} {total_raw:,} (target: {target_raw:,})")
        else:
            print(f"Raw Keywords:      {total_raw:,} (no target)")
            
        if target_filtered > 0:
            status = "✅" if abs(filtered_count - target_filtered) <= 5 else "⚠️"  # 5 keyword tolerance
            print(f"Filtered Keywords: {status} {filtered_count:,} (target: {target_filtered:,})")
        else:
            print(f"Filtered Keywords: {filtered_count:,} (no target)")
            
        if target_clusters > 0:
            status = "✅" if abs(cluster_count - target_clusters) <= 2 else "⚠️"  # 2 cluster tolerance
            print(f"Clusters:          {status} {cluster_count} (target: {target_clusters})")
        else:
            print(f"Clusters:          {cluster_count} (no target)")
            
        # Show funnel efficiency
        if total_raw > 0:
            retention_rate = (filtered_count / total_raw) * 100
            print(f"Retention Rate:    {retention_rate:.1f}% ({filtered_count:,}/{total_raw:,})")
            
        if cluster_count > 0 and filtered_count > 0:
            avg_per_cluster = filtered_count / cluster_count
            print(f"Avg per Cluster:   {avg_per_cluster:.1f} keywords")

    def _load_default_config(self) -> dict:
        """Carga configuración por defecto"""
        return {
            "database_path": "keywords.db",
            "request_delay_min": 1,
            "request_delay_max": 3,
            "max_retries": 3,
            "google_trends_hl": "es",
            "google_trends_tz": 360,
            "trend_weight": 0.4,
            "volume_weight": 0.4,
            "competition_weight": 0.2,
            "top_keywords_limit": 20,
            # Expansion controls
            "expansion_rounds": int(os.getenv("EXPANSION_ROUNDS", "1")),
            "max_new_seeds_per_round": int(os.getenv("MAX_NEW_SEEDS_PER_ROUND", "50")),
            "alphabet_soup": os.getenv("ALPHABET_SOUP", "false").lower() == "true",
            # Semantic clustering & Ads volume
            "semantic_clustering_mode": os.getenv("SEMANTIC_CLUSTERING", "auto"),  # auto|on|off
            "use_hdbscan": os.getenv("USE_HDBSCAN", "false").lower() == "true",
            "ads_volume_enabled": os.getenv("ADS_VOLUME", "on").lower() == "on",
            # Geo/Language defaults
            "geo": os.getenv("DEFAULT_GEO", "PE"),
            "language": os.getenv("DEFAULT_LANGUAGE", "es"),
        }

    def _setup_logging(self):
        """Configura el sistema de logging"""
        log_level = logging.INFO
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'keyword_finder_{datetime.now().strftime("%Y%m%d")}.log'),
            ],
        )

    async def find_keywords(  # noqa: C901
        self,
        seed_keywords: list[str],
        include_trends: bool = True,
        include_competitors: list[str] | None = None,
    ) -> tuple[list[dict], dict, list[dict]]:
        """
        Pipeline principal de búsqueda de keywords

        Args:
            seed_keywords: Keywords semilla para expandir
            include_trends: Si incluir análisis de trends
            include_competitors: Lista de dominios competidores (opcional)

        Returns:
            Tuple de (keywords rankeadas, clusters inteligentes, keywords rechazadas)
        """
        logging.info(f"Starting keyword discovery for seeds: {seed_keywords}")
        # Correlation id for this execution to tag rows in DB/exports
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        all_keywords = []

        # Fase 1: Expansión de keywords usando Google
        logging.info("Phase 1: Expanding keywords using Google sources")
        
        # Check if we need to diversify seeds for cluster targeting
        target_clusters = self.config.get("target_clusters", 0)
        if target_clusters > 0:
            seed_keywords = self._diversify_seeds_for_clusters(seed_keywords, 0)
            logging.info(f"Volume targeting: using {len(seed_keywords)} seeds for cluster diversity")

        expanded_keywords = await self.scraper.expand_keywords(
            seed_keywords, include_alphabet_soup=self.config.get("alphabet_soup", False)
        )

        # Count current raw keywords
        total_raw_count = sum(len(kws) for kws in expanded_keywords.values())
        self._last_raw_count = total_raw_count  # Store for reporting
        
        # Volume targeting: expand more if needed to reach raw target
        if self._should_expand_more(total_raw_count):
            target_raw = self.config.get("target_raw", 0)
            max_expansion_rounds = 5  # Prevent infinite loops
            round_count = 0
            
            while total_raw_count < target_raw and round_count < max_expansion_rounds:
                round_count += 1
                logging.info(f"Volume targeting: raw count {total_raw_count} < target {target_raw}, expanding (round {round_count})")
                
                # Get new seeds from current keyword pool
                seen: set[str] = set()
                for kws in expanded_keywords.values():
                    seen.update(kws)
                current_pool = list(seen)
                
                # Select promising seeds for expansion
                limit = min(50, len(current_pool))
                new_seeds = current_pool[:limit]
                
                if not new_seeds:
                    break
                    
                round_result = await self.scraper.expand_keywords(
                    new_seeds, include_alphabet_soup=self.config.get("alphabet_soup", False)
                )
                
                # Merge results
                for seed, kws in round_result.items():
                    if seed not in expanded_keywords:
                        expanded_keywords[seed] = []
                    expanded_keywords[seed].extend(kws)
                
                # Update count
                total_raw_count = sum(len(kws) for kws in expanded_keywords.values())
                self._last_raw_count = total_raw_count  # Update stored count
            
            logging.info(f"Volume targeting: reached {total_raw_count} raw keywords (target: {target_raw})")

        # Legacy iterative expansion (if configured via rounds and no volume targeting)
        elif self.config.get("target_raw", 0) == 0:
            rounds = max(1, int(self.config.get("expansion_rounds", 1)))
            if rounds > 1:
                seen: set[str] = set()
                for kws in expanded_keywords.values():
                    seen.update(kws)
                current_pool = list(seen)
                for r in range(2, rounds + 1):
                    # Select a subset of promising new seeds (limit to avoid explosion)
                    limit = int(self.config.get("max_new_seeds_per_round", 50))
                    new_seeds = current_pool[:limit]
                    if not new_seeds:
                        break
                    logging.info(f"Expansion round {r}/{rounds}: expanding {len(new_seeds)} seeds")
                    round_result = await self.scraper.expand_keywords(
                        new_seeds, include_alphabet_soup=self.config.get("alphabet_soup", False)
                    )
                    # Merge results
                    for seed, kws in round_result.items():
                        if seed not in expanded_keywords:
                            expanded_keywords[seed] = []
                        expanded_keywords[seed].extend(kws)
                    # Update pool for potential next round
                    all_kws = set()
                    for kws in round_result.values():
                        all_kws.update(kws)
                    current_pool = list(all_kws)

        for seed, keywords in expanded_keywords.items():
            for keyword in keywords:
                # Estimar volumen y competencia cuando no hay datos de trends
                estimated_volume = self.scorer.estimate_volume(keyword)
                estimated_competition = self.scorer.estimate_competition(keyword)
                category = self.scorer.categorize_keyword(keyword)

                all_keywords.append(
                    {
                        "keyword": keyword,
                        "source": f"google_{seed}",
                        "volume": estimated_volume,
                        "trend_score": 0.0,
                        "competition": estimated_competition,
                        "score": 0.0,
                        "category": category,
                    }
                )

        # Fase 2: Análisis de competidores (opcional)
        if include_competitors:
            logging.info("Phase 2: Analyzing competitor keywords")
            competitor_scraper = CompetitorScraper()

            for domain in include_competitors:
                comp_keywords = await competitor_scraper.get_competitor_keywords(domain)
                for keyword in comp_keywords:
                    all_keywords.append(
                        {
                            "keyword": keyword,
                            "source": f"competitor_{domain}",
                            "volume": 0,
                            "trend_score": 0.0,
                            "competition": 0.7,  # Asumir mayor competencia
                            "score": 0.0,
                        }
                    )

        # Fase 3: Enriquecimiento con Google Trends
        if include_trends:
            logging.info("Phase 3: Enriching with Google Trends data")
            unique_keywords = list(set([kw["keyword"] for kw in all_keywords]))

            # Procesar en batches para evitar límites de API
            batch_size = 20
            for i in range(0, len(unique_keywords), batch_size):
                batch = unique_keywords[i : i + batch_size]
                trends_data = self.trends.get_trend_data(batch)

                # Actualizar keywords con datos de trends
                for keyword_data in all_keywords:
                    keyword_text = keyword_data["keyword"]
                    if keyword_text in trends_data:
                        trend_info = trends_data[keyword_text]
                        keyword_data["trend_score"] = trend_info.get("trend_score", 0)
                        # Solo sobrescribir volumen si trends da un valor mayor
                        trends_volume = trend_info.get("volume_estimate", 0)
                        if trends_volume > keyword_data["volume"]:
                            keyword_data["volume"] = trends_volume

        # Fase 3.5: Deduplicación semántica
        logging.info("Phase 3.5: Removing duplicates and similar keywords")
        all_keywords = self.scorer.deduplicate_keywords(all_keywords, similarity_threshold=0.85)

        # Fase 3.7: Volúmenes reales desde Google Ads (si disponible)
        if self.config.get("ads_volume_enabled", True):
            try:
                logging.info("Phase 3.7: Fetching real volumes from Google Ads (if configured)")
                unique = [kw["keyword"] for kw in all_keywords]
                ads_volumes = self.ads_provider.get_volumes(
                    unique,
                    geo=self.config.get("geo", "PE"),
                    language=self.config.get("language", "es"),
                )
                if ads_volumes:
                    for kwd in all_keywords:
                        v = ads_volumes.get(kwd["keyword"])
                        if v and v > 0:
                            kwd["volume"] = int(v)
            except Exception as e:
                logging.warning(f"Ads volume integration failed; continuing with heuristics: {e}")

        # Fase 4: Categorización y filtrado
        logging.info("Phase 4: Categorizing and filtering keywords")
        all_keywords, rejected_keywords = self.categorizer.filter_keywords(
            all_keywords, min_priority=0.4
        )
        logging.info(
            f"Filtered to {len(all_keywords)} relevant keywords, rejected {len(rejected_keywords)}"
        )

        # Fase 5: Scoring y ranking
        logging.info("Phase 5: Calculating scores and ranking")
        scored_keywords = self.scorer.score_keywords_batch(all_keywords)

        # Volume targeting: Apply dynamic filtering based on targets
        target_filtered = self.config.get("target_filtered", 0)
        if target_filtered > 0:
            min_score, max_competition = self._adjust_filtering_thresholds(scored_keywords)
            
            # Apply dynamic thresholds
            filtered_keywords = []
            additional_rejected = []
            
            for kw in scored_keywords:
                if (kw.get("score", 0) >= min_score and 
                    kw.get("competition", 1) <= max_competition):
                    filtered_keywords.append(kw)
                else:
                    additional_rejected.append({
                        **kw,
                        "rejection_reason": f"volume_targeting: score={kw.get('score', 0):.1f}<{min_score:.1f} or competition={kw.get('competition', 1):.2f}>{max_competition:.2f}"
                    })
            
            # Take exactly target_filtered keywords (sorted by score)
            filtered_keywords = sorted(filtered_keywords, key=lambda x: x.get("score", 0), reverse=True)[:target_filtered]
            rejected_keywords.extend(additional_rejected)
            scored_keywords = filtered_keywords
            
            logging.info(f"Volume targeting: filtered to exactly {len(scored_keywords)} keywords (target: {target_filtered})")
        else:
            # Apply configured static thresholds
            min_score = self.config.get("min_score", 0.0)
            max_competition = self.config.get("max_competition", 1.0)
            
            if min_score > 0.0 or max_competition < 1.0:
                filtered_keywords = []
                additional_rejected = []
                
                for kw in scored_keywords:
                    if (kw.get("score", 0) >= min_score and 
                        kw.get("competition", 1) <= max_competition):
                        filtered_keywords.append(kw)
                    else:
                        additional_rejected.append({
                            **kw,
                            "rejection_reason": f"static_filter: score={kw.get('score', 0):.1f}<{min_score:.1f} or competition={kw.get('competition', 1):.2f}>{max_competition:.2f}"
                        })
                
                rejected_keywords.extend(additional_rejected)
                scored_keywords = filtered_keywords
                logging.info(f"Static filtering: kept {len(scored_keywords)} keywords (min_score≥{min_score}, max_competition≤{max_competition})")

        # Fase 4.5: Clustering inteligente de keywords
        logging.info("Phase 4.5: Creating intelligent keyword clusters")
        # Semantic clustering with mode control and graceful fallback
        clusters = {}
        mode = self.config.get("semantic_clustering_mode", "auto").lower()
        semantic = None
        if mode != "off":
            semantic = self.clusterer.fit_transform(scored_keywords)
        if semantic and mode in ("auto", "on"):
            for res in semantic:
                label_slug = res.label.strip() or "cluster"
                for item in res.keywords:
                    item["cluster_id"] = res.cluster_id
                    item["cluster_label"] = label_slug
            clusters = {
                f"{res.cluster_id:03d}_{res.label.replace(' ', '_')}": res.keywords
                for res in semantic
            }
        else:
            clusters = self.scorer.create_heuristic_clusters(scored_keywords)

        # Volume targeting: Check if we need more clusters
        target_clusters = self.config.get("target_clusters", 0)
        current_cluster_count = len(clusters)
        
        if target_clusters > 0 and current_cluster_count < target_clusters:
            logging.info(f"Volume targeting: need {target_clusters - current_cluster_count} more clusters")
            
            # If we have too few clusters, we could either:
            # 1. Split large clusters
            # 2. Re-run with more diverse seeds (would require recursive call)
            # For now, we'll split the largest clusters
            
            while len(clusters) < target_clusters and clusters:
                # Find the largest cluster
                largest_cluster_key = max(clusters.keys(), key=lambda k: len(clusters[k]))
                largest_cluster = clusters[largest_cluster_key]
                
                if len(largest_cluster) < 2:
                    break  # Can't split further
                
                # Split the cluster in half by score
                largest_cluster.sort(key=lambda x: x.get("score", 0), reverse=True)
                mid = len(largest_cluster) // 2
                
                cluster_1 = largest_cluster[:mid]
                cluster_2 = largest_cluster[mid:]
                
                # Remove original cluster and add split clusters
                del clusters[largest_cluster_key]
                
                base_name = largest_cluster_key.split('_', 1)[-1] if '_' in largest_cluster_key else "cluster"
                clusters[f"{len(clusters):03d}_{base_name}_high"] = cluster_1
                clusters[f"{len(clusters):03d}_{base_name}_mid"] = cluster_2
                
                logging.info(f"Volume targeting: split cluster {largest_cluster_key} → {len(cluster_1)} + {len(cluster_2)} keywords")
        
        elif target_clusters > 0 and current_cluster_count > target_clusters:
            # Too many clusters, merge the smallest ones
            logging.info(f"Volume targeting: merging {current_cluster_count - target_clusters} clusters")
            
            while len(clusters) > target_clusters and len(clusters) > 1:
                # Find the two smallest clusters
                sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]))
                
                # Merge the two smallest
                key1, cluster1 = sorted_clusters[0]
                key2, cluster2 = sorted_clusters[1]
                
                merged_keywords = cluster1 + cluster2
                merged_key = f"{len(clusters):03d}_merged_cluster"
                
                # Remove original clusters and add merged cluster
                del clusters[key1]
                del clusters[key2]
                clusters[merged_key] = merged_keywords
                
                logging.info(f"Volume targeting: merged {key1} + {key2} → {len(merged_keywords)} keywords")
        
        logging.info(f"Created {len(clusters)} keyword clusters (target: {target_clusters or 'auto'})")
        
        # Update cluster metadata for all keywords
        for cid, items in clusters.items():
            for it in items:
                it["cluster_id"] = int(cid.split("_", 1)[0]) if "_" in cid else 0
                it["cluster_label"] = (
                    cid.split("_", 1)[1].replace("_", " ") if "_" in cid else cid
                )

        # Fase 5: Guardar en base de datos
        logging.info("Phase 5: Saving to database")
        keyword_objects = []
        for kw_data in scored_keywords:
            keyword_obj = Keyword(
                keyword=kw_data["keyword"],
                source=kw_data["source"],
                volume=kw_data["volume"],
                trend_score=kw_data["trend_score"],
                competition=kw_data["competition"],
                score=kw_data["score"],
                category=kw_data.get("category", ""),
                geo=self.config.get("geo", ""),
                language=self.config.get("language", ""),
                intent=kw_data.get("intent", ""),
                cluster_id=kw_data.get("cluster_id"),
                cluster_label=kw_data.get("cluster_label"),
                run_id=run_id,
                trend_weight=self.config.get("trend_weight", 0.4),
                volume_weight=self.config.get("volume_weight", 0.4),
                competition_weight=self.config.get("competition_weight", 0.2),
                intent_prob=float(kw_data.get("intent_prob", 0.0) or 0.0),
            )
            keyword_objects.append(keyword_obj)

        self.db.insert_keywords_batch(keyword_objects)

        logging.info(f"Keyword discovery completed. Found {len(scored_keywords)} keywords")
        return scored_keywords, clusters, rejected_keywords

    async def generate_reports(
        self,
        keywords: list[dict],
        export_formats: list[str] | None = None,
        clusters: dict | None = None,
    ) -> dict[str, str]:
        """
        Genera reportes en los formatos especificados

        Args:
            keywords: Lista de keywords procesadas
            export_formats: Formatos a exportar ['csv', 'pdf']
            clusters: Clusters de keywords (opcional)

        Returns:
            Dict con paths de archivos generados
        """
        generated_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Limitar a top keywords para reportes
        top_keywords = keywords[: self.config["top_keywords_limit"]]

        # Establecer formatos por defecto de forma segura
        if export_formats is None:
            export_formats = ["csv", "pdf"]

        if "csv" in export_formats:
            csv_file = self.exporter.export_to_csv(keywords, f"keyword_analysis_{timestamp}.csv")
            generated_files["csv"] = csv_file
            logging.info(f"CSV report generated: {csv_file}")

            # Exportar reportes de clusters si están disponibles
            if clusters:
                cluster_report_file = self.exporter.export_cluster_report(
                    clusters, f"cluster_report_{timestamp}.csv"
                )
                cluster_summary_file = self.exporter.export_clusters_summary(
                    clusters, f"clusters_summary_{timestamp}.csv"
                )
                generated_files["cluster_report"] = cluster_report_file
                generated_files["cluster_summary"] = cluster_summary_file
                logging.info(
                    f"Cluster reports generated: {cluster_report_file}, {cluster_summary_file}"
                )

        if "pdf" in export_formats:
            pdf_file = self.exporter.export_to_pdf(
                top_keywords,
                f"keyword_report_{timestamp}.pdf",
                title=f"Keyword Research Report - {datetime.now().strftime('%d/%m/%Y')}",
            )
            generated_files["pdf"] = pdf_file
            logging.info(f"PDF report generated: {pdf_file}")

        # Briefs por cluster (Markdown) cuando se solicita
        if "briefs" in export_formats and clusters:
            briefs_dir = self.exporter.export_briefs(
                clusters,
                dirname=f"briefs_{timestamp}",
                geo=self.config.get("geo"),
            )
            generated_files["briefs"] = briefs_dir
            logging.info(f"Briefs generated in directory: {briefs_dir}")

        return generated_files

    def get_existing_keywords(self, filters: dict | None = None) -> list[dict]:
        """Obtiene keywords existentes de la base de datos"""
        return self.db.get_keywords(
            limit=filters.get("limit") if filters else None,
            min_score=filters.get("min_score", 0) if filters else 0,
        )

    def get_stats(self) -> dict:
        """Obtiene estadísticas de la base de datos"""
        return self.db.get_stats()

    async def cleanup(self):
        """Limpia recursos"""
        await self.scraper.close()
        logging.info("Resources cleaned up")


async def main():  # noqa: C901
    """Función principal del CLI"""
    parser = argparse.ArgumentParser(
        description="Keyword Finder - Descubrimiento automático de keywords",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py --seeds "marketing pymes" "limpieza piscinas"
  python main.py --seeds "marketing digital" --export csv pdf
  python main.py --seeds "curso python" --competitors "udemy.com" "coursera.org"
  python main.py --stats
        """,
    )

    parser.add_argument("--seeds", nargs="+", help="Keywords semilla para expandir")

    parser.add_argument(
        "--seeds-file", type=str, help="Ruta a un archivo de texto con seeds (una por línea)"
    )

    parser.add_argument(
        "--export",
        nargs="+",
        choices=["csv", "pdf", "briefs"],
        default=["csv"],
        help="Formatos de export (default: csv)",
    )

    parser.add_argument("--competitors", nargs="+", help="Dominios competidores para analizar")

    parser.add_argument("--no-trends", action="store_true", help="Omitir análisis de Google Trends")

    parser.add_argument(
        "--ads-volume",
        choices=["on", "off"],
        default=os.getenv("ADS_VOLUME", "on"),
        help="Usar Google Ads Keyword Planner para volúmenes reales (requiere credenciales)",
    )

    parser.add_argument(
        "--semantic-clustering",
        choices=["auto", "on", "off"],
        default=os.getenv("SEMANTIC_CLUSTERING", "auto"),
        help="Clustering semántico: auto intenta con fallback; on obliga; off desactiva",
    )

    parser.add_argument(
        "--hdbscan",
        action="store_true",
        help="Intentar HDBSCAN para clustering denso si está instalado",
    )

    parser.add_argument("--geo", default=os.getenv("DEFAULT_GEO", "PE"), help="Geo país (ISO)")
    parser.add_argument(
        "--language", default=os.getenv("DEFAULT_LANGUAGE", "es"), help="Idioma (ISO)"
    )

    parser.add_argument(
        "--limit", type=int, default=20, help="Límite de keywords en reportes (default: 20)"
    )

    parser.add_argument(
        "--stats", action="store_true", help="Mostrar estadísticas de la base de datos"
    )

    parser.add_argument(
        "--existing",
        action="store_true",
        help="Mostrar keywords existentes en lugar de buscar nuevas",
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=int(os.getenv("EXPANSION_ROUNDS", "1")),
        help="Rondas de expansión iterativa (default: 1)",
    )

    parser.add_argument(
        "--alphabet-soup",
        action="store_true",
        help="Activa variaciones tipo 'alphabet soup' (a-z, 0-9) para ampliar sugerencias",
    )

    parser.add_argument(
        "--filters",
        type=str,
        default="",
        help='Filtros para --existing en formato k=v separados por coma (ej: "geo=PE,language=es,intent=transactional,score>=60,last_seen_after=2025-09-01T00:00:00")',
    )

    # Volume targeting controls
    parser.add_argument(
        "--target-raw",
        type=int,
        default=0,
        help="Target raw keywords count (0=no limit). System will expand seeds until this target is reached.",
    )

    parser.add_argument(
        "--target-filtered",
        type=int,
        default=0,
        help="Target filtered keywords count (0=no limit). System will adjust filtering thresholds to hit this target.",
    )

    parser.add_argument(
        "--target-clusters",
        type=int,
        default=0,
        help="Target cluster count (0=no limit). System will diversify seeds to generate this many clusters.",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum score threshold for filtered keywords (0-100, default: 0.0)",
    )

    parser.add_argument(
        "--max-competition",
        type=float,
        default=1.0,
        help="Maximum competition threshold for filtered keywords (0-1, default: 1.0)",
    )

    args = parser.parse_args()

    # Crear instancia del keyword finder
    finder = KeywordFinder(
        config={
            "semantic_clustering_mode": args.semantic_clustering,
            "use_hdbscan": bool(args.hdbscan),
            "ads_volume_enabled": args.ads_volume == "on",
            "geo": args.geo,
            "language": args.language,
            "expansion_rounds": max(1, int(args.rounds)),
            "alphabet_soup": bool(args.alphabet_soup),
            # Volume targeting controls
            "target_raw": args.target_raw,
            "target_filtered": args.target_filtered,
            "target_clusters": args.target_clusters,
            "min_score": args.min_score,
            "max_competition": args.max_competition,
        }
    )

    try:
        # Mostrar estadísticas
        if args.stats:
            stats = finder.get_stats()
            print("\n📊 Estadísticas de la Base de Datos:")
            print(f"Total keywords: {stats.get('total_keywords', 0)}")
            avg_score = stats.get("avg_score") or 0
            max_score = stats.get("max_score") or 0
            print(f"Score promedio: {avg_score:.2f}")
            print(f"Score máximo: {max_score:.2f}")
            print(f"Keywords de alto score (>70): {stats.get('high_score_count', 0)}")

            if stats.get("sources"):
                print("\nFuentes:")
                for source, count in stats["sources"].items():
                    print(f"  {source}: {count} keywords")
            return

        # Mostrar keywords existentes
        if args.existing:
            # Parse filters string
            filters: dict[str, str] = {}
            min_score = 0
            if args.filters:
                parts = [p.strip() for p in args.filters.split(",") if p.strip()]
                for p in parts:
                    if ">=" in p:
                        key, value = p.split(">=", 1)
                        if key.strip() == "score":
                            try:
                                min_score = float(value)
                            except ValueError:
                                pass
                    elif "=" in p:
                        key, value = p.split("=", 1)
                        filters[key.strip()] = value.strip()

            keywords = finder.db.get_keywords(
                limit=args.limit, min_score=min_score, filters=filters
            )

            if not keywords:
                print("No hay keywords en la base de datos.")
                return

            print(f"\n🔍 Top {len(keywords)} Keywords Existentes:")
            for i, kw in enumerate(keywords, 1):
                print(
                    f"{i:2d}. {kw['keyword']:<30} Score: {kw['score']:5.1f} | "
                    f"Trend: {kw['trend_score']:3.0f} | Source: {kw['source']}"
                )

            # Generar reportes de keywords existentes
            if args.export:
                print(f"\n📄 Generando reportes en formatos: {', '.join(args.export)}")
                reports = await finder.generate_reports(keywords, args.export)
                for format_type, filepath in reports.items():
                    print(f"✅ {format_type.upper()}: {filepath}")

            return

        # Construir lista de seeds desde CLI y/o archivo
        all_seeds: list[str] = []
        if args.seeds:
            all_seeds.extend(args.seeds)
        if args.seeds_file:
            try:
                from pathlib import Path

                seed_path = Path(args.seeds_file)
                if not seed_path.exists():
                    raise FileNotFoundError(f"No existe el archivo: {seed_path}")
                with seed_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if s and not s.startswith("#"):
                            all_seeds.append(s)
            except Exception as e:
                logging.error(f"No se pudieron leer seeds desde archivo: {e}")
                print(f"❌ Error leyendo --seeds-file: {e}")
                return

        # Deduplicar y validar
        all_seeds = sorted({s.strip() for s in all_seeds if s and len(s.strip()) >= 2})
        if not all_seeds:
            print("❌ Error: Debes proporcionar keywords semilla con --seeds o --seeds-file")
            parser.print_help()
            return

        print(
            f"🚀 Iniciando búsqueda de keywords para: {', '.join(all_seeds[:10])}{' ...' if len(all_seeds) > 10 else ''}"
        )

        # Ejecutar búsqueda de keywords
        start_ts = datetime.now()
        keywords, clusters, rejected = await finder.find_keywords(
            seed_keywords=all_seeds,
            include_trends=not args.no_trends,
            include_competitors=args.competitors,
        )

        if not keywords:
            print("❌ No se encontraron keywords.")
            return

        # Calculate raw keyword count for targeting summary
        total_raw_count = getattr(finder, '_last_raw_count', len(keywords) * 2)  # Use stored count or estimate

        # Show volume targeting summary if any targets are set
        if (finder.config.get("target_raw", 0) > 0 or 
            finder.config.get("target_filtered", 0) > 0 or 
            finder.config.get("target_clusters", 0) > 0):
            finder._print_volume_targeting_summary(
                total_raw=total_raw_count,
                filtered_count=len(keywords), 
                cluster_count=len(clusters)
            )

        # Mostrar resultados
        top_keywords = keywords[: args.limit]
        print(f"\n🎯 Top {len(top_keywords)} Keywords encontradas:")
        print("-" * 80)

        for i, kw in enumerate(top_keywords, 1):
            print(
                f"{i:2d}. {kw['keyword']:<30} Score: {kw['score']:5.1f} | "
                f"Trend: {kw['trend_score']:3.0f} | Volume: {kw['volume']:5d} | "
                f"Comp: {kw['competition']:4.2f}"
            )

        # Generar reportes
        print(f"\n📄 Generando reportes en formatos: {', '.join(args.export)}")
        reports = await finder.generate_reports(keywords, args.export, clusters)

        for format_type, filepath in reports.items():
            print(f"✅ {format_type.upper()}: {filepath}")

        # Generate reliability report
        generate_reliability_report(top_keywords, rejected)

        # Persist run metrics
        try:
            from json import dumps

            finder.db.insert_run(
                run_id=f"run_{start_ts.strftime('%Y%m%d_%H%M%S')}",
                metrics={
                    "started_at": start_ts.isoformat(),
                    "finished_at": datetime.now().isoformat(),
                    "geo": args.geo,
                    "language": args.language,
                    "seeds_json": dumps(all_seeds, ensure_ascii=False),
                    "seeds_count": len(all_seeds),
                    "keywords_found": len(keywords),
                    "rejected_count": len(rejected),
                    "trend_weight": finder.config.get("trend_weight", 0.4),
                    "volume_weight": finder.config.get("volume_weight", 0.4),
                    "competition_weight": finder.config.get("competition_weight", 0.2),
                    "duration_ms": int((datetime.now() - start_ts).total_seconds() * 1000),
                },
            )
        except Exception as e:
            logging.debug(f"Failed to persist run metrics: {e}")

        print(f"\n✨ Proceso completado. {len(keywords)} keywords procesadas y guardadas.")

    except KeyboardInterrupt:
        print("\n🛑 Proceso interrumpido por el usuario.")
    except Exception as e:
        logging.error(f"Error en ejecución principal: {e}")
        print(f"❌ Error: {e}")
    finally:
        await finder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
