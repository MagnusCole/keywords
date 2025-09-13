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
from typing import List, Dict, Optional

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

from database import KeywordDatabase, Keyword
from scrapers import GoogleScraper, CompetitorScraper
from trends import TrendsAnalyzer
from scoring import KeywordScorer
from exporters import KeywordExporter

class KeywordFinder:
    """Orquestador principal del sistema de keyword finding"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_default_config()
        self._setup_logging()
        
        # Inicializar componentes
        self.db = KeywordDatabase(self.config['database_path'])
        self.scraper = GoogleScraper(
            delay_range=(self.config['request_delay_min'], self.config['request_delay_max']),
            max_retries=self.config['max_retries']
        )
        self.trends = TrendsAnalyzer(
            hl=self.config['google_trends_hl'],
            tz=self.config['google_trends_tz']
        )
        self.scorer = KeywordScorer(
            trend_weight=self.config['trend_weight'],
            volume_weight=self.config['volume_weight'],
            competition_weight=self.config['competition_weight']
        )
        self.exporter = KeywordExporter()
        
        logging.info("KeywordFinder initialized successfully")
    
    def _load_default_config(self) -> Dict:
        """Carga configuración por defecto"""
        return {
            'database_path': 'keywords.db',
            'request_delay_min': 1,
            'request_delay_max': 3,
            'max_retries': 3,
            'google_trends_hl': 'es',
            'google_trends_tz': 360,
            'trend_weight': 0.4,
            'volume_weight': 0.4,
            'competition_weight': 0.2,
            'top_keywords_limit': 20
        }
    
    def _setup_logging(self):
        """Configura el sistema de logging"""
        log_level = logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'keyword_finder_{datetime.now().strftime("%Y%m%d")}.log')
            ]
        )
    
    async def find_keywords(self, seed_keywords: List[str], 
                          include_trends: bool = True,
                          include_competitors: Optional[List[str]] = None) -> List[Dict]:
        """
        Pipeline principal de búsqueda de keywords
        
        Args:
            seed_keywords: Keywords semilla para expandir
            include_trends: Si incluir análisis de trends
            include_competitors: Lista de dominios competidores (opcional)
        
        Returns:
            Lista de keywords rankeadas con scores
        """
        logging.info(f"Starting keyword discovery for seeds: {seed_keywords}")
        
        all_keywords = []
        
        # Fase 1: Expansión de keywords usando Google
        logging.info("Phase 1: Expanding keywords using Google sources")
        expanded_keywords = await self.scraper.expand_keywords(seed_keywords)
        
        for seed, keywords in expanded_keywords.items():
            for keyword in keywords:
                all_keywords.append({
                    'keyword': keyword,
                    'source': f'google_{seed}',
                    'volume': 0,
                    'trend_score': 0.0,
                    'competition': 0.5,
                    'score': 0.0
                })
        
        # Fase 2: Análisis de competidores (opcional)
        if include_competitors:
            logging.info("Phase 2: Analyzing competitor keywords")
            competitor_scraper = CompetitorScraper()
            
            for domain in include_competitors:
                comp_keywords = await competitor_scraper.get_competitor_keywords(domain)
                for keyword in comp_keywords:
                    all_keywords.append({
                        'keyword': keyword,
                        'source': f'competitor_{domain}',
                        'volume': 0,
                        'trend_score': 0.0,
                        'competition': 0.7,  # Asumir mayor competencia
                        'score': 0.0
                    })
        
        # Fase 3: Enriquecimiento con Google Trends
        if include_trends:
            logging.info("Phase 3: Enriching with Google Trends data")
            unique_keywords = list(set([kw['keyword'] for kw in all_keywords]))
            
            # Procesar en batches para evitar límites de API
            batch_size = 20
            for i in range(0, len(unique_keywords), batch_size):
                batch = unique_keywords[i:i + batch_size]
                trends_data = self.trends.get_trend_data(batch)
                
                # Actualizar keywords con datos de trends
                for keyword_data in all_keywords:
                    keyword_text = keyword_data['keyword']
                    if keyword_text in trends_data:
                        trend_info = trends_data[keyword_text]
                        keyword_data['trend_score'] = trend_info.get('trend_score', 0)
                        keyword_data['volume'] = trend_info.get('volume_estimate', 0)
        
        # Fase 4: Scoring y ranking
        logging.info("Phase 4: Calculating scores and ranking")
        scored_keywords = self.scorer.score_keywords_batch(all_keywords)
        
        # Fase 5: Guardar en base de datos
        logging.info("Phase 5: Saving to database")
        keyword_objects = []
        for kw_data in scored_keywords:
            keyword_obj = Keyword(
                keyword=kw_data['keyword'],
                source=kw_data['source'],
                volume=kw_data['volume'],
                trend_score=kw_data['trend_score'],
                competition=kw_data['competition'],
                score=kw_data['score']
            )
            keyword_objects.append(keyword_obj)
        
        self.db.insert_keywords_batch(keyword_objects)
        
        logging.info(f"Keyword discovery completed. Found {len(scored_keywords)} keywords")
        return scored_keywords
    
    async def generate_reports(self, keywords: List[Dict], 
                             export_formats: List[str] = ['csv', 'pdf']) -> Dict[str, str]:
        """
        Genera reportes en los formatos especificados
        
        Args:
            keywords: Lista de keywords procesadas
            export_formats: Formatos a exportar ['csv', 'pdf']
        
        Returns:
            Dict con paths de archivos generados
        """
        generated_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Limitar a top keywords para reportes
        top_keywords = keywords[:self.config['top_keywords_limit']]
        
        if 'csv' in export_formats:
            csv_file = self.exporter.export_to_csv(
                keywords, 
                f"keyword_analysis_{timestamp}.csv"
            )
            generated_files['csv'] = csv_file
            logging.info(f"CSV report generated: {csv_file}")
        
        if 'pdf' in export_formats:
            pdf_file = self.exporter.export_to_pdf(
                top_keywords,
                f"keyword_report_{timestamp}.pdf",
                title=f"Keyword Research Report - {datetime.now().strftime('%d/%m/%Y')}"
            )
            generated_files['pdf'] = pdf_file
            logging.info(f"PDF report generated: {pdf_file}")
        
        return generated_files
    
    def get_existing_keywords(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Obtiene keywords existentes de la base de datos"""
        return self.db.get_keywords(
            limit=filters.get('limit') if filters else None,
            min_score=filters.get('min_score', 0) if filters else 0
        )
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de la base de datos"""
        return self.db.get_stats()
    
    async def cleanup(self):
        """Limpia recursos"""
        await self.scraper.close()
        logging.info("Resources cleaned up")

async def main():
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
        """
    )
    
    parser.add_argument(
        '--seeds', 
        nargs='+', 
        help='Keywords semilla para expandir'
    )
    
    parser.add_argument(
        '--export', 
        nargs='+', 
        choices=['csv', 'pdf'],
        default=['csv'],
        help='Formatos de export (default: csv)'
    )
    
    parser.add_argument(
        '--competitors',
        nargs='+',
        help='Dominios competidores para analizar'
    )
    
    parser.add_argument(
        '--no-trends',
        action='store_true',
        help='Omitir análisis de Google Trends'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Límite de keywords en reportes (default: 20)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas de la base de datos'
    )
    
    parser.add_argument(
        '--existing',
        action='store_true',
        help='Mostrar keywords existentes en lugar de buscar nuevas'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del keyword finder
    finder = KeywordFinder()
    
    try:
        # Mostrar estadísticas
        if args.stats:
            stats = finder.get_stats()
            print("\n📊 Estadísticas de la Base de Datos:")
            print(f"Total keywords: {stats.get('total_keywords', 0)}")
            avg_score = stats.get('avg_score') or 0
            max_score = stats.get('max_score') or 0
            print(f"Score promedio: {avg_score:.2f}")
            print(f"Score máximo: {max_score:.2f}")
            print(f"Keywords de alto score (>70): {stats.get('high_score_count', 0)}")
            
            if stats.get('sources'):
                print("\nFuentes:")
                for source, count in stats['sources'].items():
                    print(f"  {source}: {count} keywords")
            return
        
        # Mostrar keywords existentes
        if args.existing:
            keywords = finder.get_existing_keywords({'limit': args.limit})
            
            if not keywords:
                print("No hay keywords en la base de datos.")
                return
            
            print(f"\n🔍 Top {len(keywords)} Keywords Existentes:")
            for i, kw in enumerate(keywords, 1):
                print(f"{i:2d}. {kw['keyword']:<30} Score: {kw['score']:5.1f} | "
                      f"Trend: {kw['trend_score']:3.0f} | Source: {kw['source']}")
            
            # Generar reportes de keywords existentes
            if args.export:
                print(f"\n📄 Generando reportes en formatos: {', '.join(args.export)}")
                reports = await finder.generate_reports(keywords, args.export)
                for format_type, filepath in reports.items():
                    print(f"✅ {format_type.upper()}: {filepath}")
            
            return
        
        # Validar seeds
        if not args.seeds:
            print("❌ Error: Debes proporcionar keywords semilla con --seeds")
            parser.print_help()
            return
        
        print(f"🚀 Iniciando búsqueda de keywords para: {', '.join(args.seeds)}")
        
        # Ejecutar búsqueda de keywords
        keywords = await finder.find_keywords(
            seed_keywords=args.seeds,
            include_trends=not args.no_trends,
            include_competitors=args.competitors
        )
        
        if not keywords:
            print("❌ No se encontraron keywords.")
            return
        
        # Mostrar resultados
        top_keywords = keywords[:args.limit]
        print(f"\n🎯 Top {len(top_keywords)} Keywords encontradas:")
        print("-" * 80)
        
        for i, kw in enumerate(top_keywords, 1):
            print(f"{i:2d}. {kw['keyword']:<30} Score: {kw['score']:5.1f} | "
                  f"Trend: {kw['trend_score']:3.0f} | Volume: {kw['volume']:5d} | "
                  f"Comp: {kw['competition']:4.2f}")
        
        # Generar reportes
        print(f"\n📄 Generando reportes en formatos: {', '.join(args.export)}")
        reports = await finder.generate_reports(keywords, args.export)
        
        for format_type, filepath in reports.items():
            print(f"✅ {format_type.upper()}: {filepath}")
        
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