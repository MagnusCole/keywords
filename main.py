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
from pathlib import Path
from typing import Any

# Agregar el directorio src al path para importar módulos
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from keyword_finder.core.ads_volume import GoogleAdsVolumeProvider  # noqa: E402
from keyword_finder.core.categorization import KeywordCategorizer  # noqa: E402
from keyword_finder.core.clustering import SemanticClusterer  # noqa: E402
from keyword_finder.core.database import Keyword, KeywordDatabase  # noqa: E402
from keyword_finder.core.exporters import KeywordExporter  # noqa: E402
from keyword_finder.core.scoring import AdvancedKeywordScorer  # noqa: E402
from keyword_finder.core.scrapers import GoogleScraper  # noqa: E402
from keyword_finder.core.trends import GoogleTrendsAnalyzer  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError as _e:
    logging.debug("dotenv not loaded (module missing): %s", _e)


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
        self.trends = GoogleTrendsAnalyzer(
            hl=self.config["google_trends_hl"], tz=self.config["google_trends_tz"]
        )
        self.scorer = AdvancedKeywordScorer(
            target_geo=self.config.get("target_geo", "PE"),
            target_intent=self.config.get("target_intent", "transactional"),
        )
        self.exporter = KeywordExporter()
        self.clusterer = SemanticClusterer(use_hdbscan=self.config.get("use_hdbscan", False))
        self.ads_provider = GoogleAdsVolumeProvider()
        self.categorizer = KeywordCategorizer(
            target_geo=self.config["geo"], target_business="services"
        )

        logging.info("KeywordFinder initialized successfully")

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
        logging.info("Starting keyword discovery for seeds: %s", seed_keywords)
        # Correlation id for this execution to tag rows in DB/exports
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        all_keywords = []

        # Fase 1: Expansión de keywords usando Google
        logging.info("Phase 1: Expanding keywords using Google sources")
        expanded_keywords = await self.scraper.expand_keywords(seed_keywords)

        for seed, keywords in expanded_keywords.items():
            for keyword in keywords:
                # Usar valores por defecto ya que los métodos de estimación no están disponibles
                estimated_volume = 0  # self.scorer.estimate_volume(keyword)
                estimated_competition = 0.5  # self.scorer.estimate_competition(keyword)
                category = "unknown"  # self.scorer.categorize_keyword(keyword)

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

        # Fase 2: Análisis de competidores (deshabilitado - CompetitorScraper no disponible)
        if include_competitors:
            logging.warning("Competitor analysis disabled - CompetitorScraper not available")

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

        # Fase 3.5: Deduplicación semántica (deshabilitada - método no disponible)
        logging.info("Phase 3.5: Removing duplicates and similar keywords (skipped)")
        # all_keywords = self.scorer.deduplicate_keywords(all_keywords, similarity_threshold=0.85)

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
            except (KeyError, ValueError, TypeError) as e:
                logging.warning("Ads volume integration failed; continuing with heuristics: %s", e)

        # Fase 4: Categorización y filtrado
        logging.info("Phase 4: Categorizing and filtering keywords")
        all_keywords, rejected_keywords = self.categorizer.filter_keywords(
            all_keywords, min_priority=0.4
        )
        logging.info(
            "Filtered to %d relevant keywords, rejected %d",
            len(all_keywords),
            len(rejected_keywords),
        )

        # Fase 5: Scoring y ranking
        logging.info("Phase 5: Calculating scores and ranking")
        scored_keywords = self.scorer.calculate_advanced_score(all_keywords)

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
            # Fallback: crear clusters simples por fuente
            logging.warning("Using simple fallback clustering")
            clusters = {}
            for kw in scored_keywords:
                source = kw.get("source", "unknown")
                if source not in clusters:
                    clusters[source] = []
                clusters[source].append(kw)
                kw["cluster_id"] = hash(source) % 1000  # Simple ID
                kw["cluster_label"] = source
        logging.info("Created %d keyword clusters", len(clusters))

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

        logging.info("Keyword discovery completed. Found %d keywords", len(scored_keywords))
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
            logging.info("CSV report generated: %s", csv_file)

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
                    "Cluster reports generated: %s, %s", cluster_report_file, cluster_summary_file
                )

        if "pdf" in export_formats:
            pdf_file = self.exporter.export_to_pdf(
                top_keywords,
                f"keyword_report_{timestamp}.pdf",
                title=f"Keyword Research Report - {datetime.now().strftime('%d/%m/%Y')}",
            )
            generated_files["pdf"] = pdf_file
            logging.info("PDF report generated: %s", pdf_file)

        return generated_files

    def get_existing_keywords(self, filters: dict | None = None) -> list[dict[str, Any]]:
        """Obtiene keywords existentes de la base de datos"""
        return self.db.get_keywords(
            limit=filters.get("limit") if filters else None,
            min_score=filters.get("min_score", 0) if filters else 0,
        )

    def get_stats(self) -> dict[str, Any]:
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
        choices=["csv", "pdf"],
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
        "--filters",
        type=str,
        default="",
        help='Filtros para --existing en formato k=v separados por coma (ej: "geo=PE,language=es,intent=transactional,score>=60,last_seen_after=2025-09-01T00:00:00")',
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
                seed_path = Path(args.seeds_file)
                if not seed_path.exists():
                    raise FileNotFoundError(f"No existe el archivo: {seed_path}")
                with seed_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if s and not s.startswith("#"):
                            all_seeds.append(s)
            except (OSError, FileNotFoundError) as e:
                logging.error("No se pudieron leer seeds desde archivo: %s", e)
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

        # Generate reliability report (deshabilitado - función no disponible)
        # generate_reliability_report(top_keywords, rejected)

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
        except (OSError, ValueError, TypeError) as e:
            logging.debug("Failed to persist run metrics: %s", e)

        print(f"\n✨ Proceso completado. {len(keywords)} keywords procesadas y guardadas.")

    except KeyboardInterrupt:
        print("\n🛑 Proceso interrumpido por el usuario.")
    except Exception as e:
        logging.error("Error en ejecución principal: %s", e)
        print(f"❌ Error: {e}")
    finally:
        await finder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
