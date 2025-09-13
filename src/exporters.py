import csv
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from io import BytesIO
import base64

class KeywordExporter:
    """Exportador de keywords a diferentes formatos (CSV, PDF)"""
    
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        logging.info(f"KeywordExporter initialized with export directory: {self.export_dir}")
    
    def export_to_csv(self, keywords: List[Dict], filename: Optional[str] = None) -> str:
        """
        Exporta keywords a archivo CSV
        
        Args:
            keywords: Lista de keywords con datos
            filename: Nombre del archivo (opcional)
        
        Returns:
            Path del archivo generado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keywords_{timestamp}.csv"
        
        filepath = self.export_dir / filename
        
        try:
            if not keywords:
                logging.warning("No keywords to export")
                return str(filepath)
            
            # Definir columnas del CSV
            fieldnames = [
                'rank', 'keyword', 'source', 'score', 'trend_score', 
                'volume', 'competition', 'last_seen', 'category'
            ]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, keyword in enumerate(keywords, 1):
                    row = {
                        'rank': i,
                        'keyword': keyword.get('keyword', ''),
                        'source': keyword.get('source', ''),
                        'score': keyword.get('score', 0),
                        'trend_score': keyword.get('trend_score', 0),
                        'volume': keyword.get('volume', 0),
                        'competition': keyword.get('competition', 0),
                        'last_seen': keyword.get('last_seen', ''),
                        'category': self._categorize_keyword(keyword.get('score', 0))
                    }
                    writer.writerow(row)
            
            logging.info(f"Exported {len(keywords)} keywords to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return ""
    
    def export_to_pdf(self, keywords: List[Dict], filename: Optional[str] = None,
                     title: str = "Keyword Research Report") -> str:
        """
        Exporta keywords a reporte PDF
        
        Args:
            keywords: Lista de keywords con datos
            filename: Nombre del archivo (opcional)
            title: Título del reporte
        
        Returns:
            Path del archivo generado
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keyword_report_{timestamp}.pdf"
        
        filepath = self.export_dir / filename
        
        try:
            # Crear documento PDF
            doc = SimpleDocTemplate(str(filepath), pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Título del reporte
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.darkblue
            )
            story.append(Paragraph(title, title_style))
            
            # Información del reporte
            info_text = f"""
            <b>Fecha de generación:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}<br/>
            <b>Total de keywords analizadas:</b> {len(keywords)}<br/>
            <b>Top keywords mostradas:</b> {min(20, len(keywords))}
            """
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Resumen ejecutivo
            if keywords:
                summary = self._generate_executive_summary(keywords[:20])
                story.append(Paragraph("<b>Resumen Ejecutivo</b>", styles['Heading2']))
                story.append(Paragraph(summary, styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Tabla de top keywords
            if keywords:
                story.append(Paragraph("<b>Top 20 Keywords</b>", styles['Heading2']))
                table_data = self._prepare_table_data(keywords[:20])
                table = Table(table_data)
                
                # Estilo de la tabla
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
            
            # Análisis por categorías
            if keywords:
                story.append(Paragraph("<b>Análisis por Categorías</b>", styles['Heading2']))
                category_analysis = self._analyze_categories(keywords)
                story.append(Paragraph(category_analysis, styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Recomendaciones
            story.append(Paragraph("<b>Recomendaciones</b>", styles['Heading2']))
            recommendations = self._generate_recommendations(keywords[:20])
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles['Normal']))
            
            # Generar PDF
            doc.build(story)
            
            logging.info(f"Exported PDF report: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logging.error(f"Error exporting to PDF: {e}")
            return ""
    
    def _prepare_table_data(self, keywords: List[Dict]) -> List[List[str]]:
        """Prepara datos para la tabla del PDF"""
        headers = ['Rank', 'Keyword', 'Score', 'Trend', 'Volume', 'Competition', 'Source']
        table_data = [headers]
        
        for i, kw in enumerate(keywords, 1):
            row = [
                str(i),
                kw.get('keyword', '')[:30] + ('...' if len(kw.get('keyword', '')) > 30 else ''),
                f"{kw.get('score', 0):.1f}",
                f"{kw.get('trend_score', 0):.0f}",
                f"{kw.get('volume', 0):,}",
                f"{kw.get('competition', 0):.2f}",
                kw.get('source', '')[:15]
            ]
            table_data.append(row)
        
        return table_data
    
    def _generate_executive_summary(self, keywords: List[Dict]) -> str:
        """Genera resumen ejecutivo del análisis"""
        if not keywords:
            return "No se encontraron keywords para analizar."
        
        # Estadísticas básicas
        avg_score = sum(kw.get('score', 0) for kw in keywords) / len(keywords)
        high_score_count = len([kw for kw in keywords if kw.get('score', 0) > 70])
        avg_competition = sum(kw.get('competition', 0) for kw in keywords) / len(keywords)
        
        # Fuentes más productivas
        sources = {}
        for kw in keywords:
            source = kw.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        top_source = max(sources.items(), key=lambda x: x[1]) if sources else ('N/A', 0)
        
        summary = f"""
        El análisis reveló {len(keywords)} keywords de alto potencial con un score promedio de {avg_score:.1f}/100.
        Se identificaron {high_score_count} keywords excelentes (score > 70) que representan oportunidades prioritarias.
        El nivel promedio de competencia es de {avg_competition:.2f}, indicando un mercado {'competitivo' if avg_competition > 0.6 else 'moderado'}.
        La fuente más productiva fue '{top_source[0]}' con {top_source[1]} keywords relevantes.
        """
        
        return summary.strip()
    
    def _analyze_categories(self, keywords: List[Dict]) -> str:
        """Analiza keywords por categorías de score"""
        categories = {
            'excelente': 0,    # 80-100
            'buena': 0,        # 60-79
            'promedio': 0,     # 40-59
            'baja': 0,         # 20-39
            'muy_baja': 0      # 0-19
        }
        
        for kw in keywords:
            score = kw.get('score', 0)
            category = self._categorize_keyword(score)
            categories[category] += 1
        
        total = len(keywords)
        analysis = f"""
        <b>Distribución por calidad:</b><br/>
        • Excelentes (80-100): {categories['excelente']} keywords ({categories['excelente']/total*100:.1f}%)<br/>
        • Buenas (60-79): {categories['buena']} keywords ({categories['buena']/total*100:.1f}%)<br/>
        • Promedio (40-59): {categories['promedio']} keywords ({categories['promedio']/total*100:.1f}%)<br/>
        • Bajas (20-39): {categories['baja']} keywords ({categories['baja']/total*100:.1f}%)<br/>
        • Muy bajas (0-19): {categories['muy_baja']} keywords ({categories['muy_baja']/total*100:.1f}%)
        """
        
        return analysis
    
    def _categorize_keyword(self, score: float) -> str:
        """Categoriza keyword por score"""
        if score >= 80:
            return "excelente"
        elif score >= 60:
            return "buena"
        elif score >= 40:
            return "promedio"
        elif score >= 20:
            return "baja"
        else:
            return "muy_baja"
    
    def _generate_recommendations(self, keywords: List[Dict]) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        if not keywords:
            return ["No hay datos suficientes para generar recomendaciones."]
        
        recommendations = []
        
        # Top 3 keywords
        top_keywords = [kw.get('keyword', '') for kw in keywords[:3]]
        recommendations.append(
            f"Priorizar contenido para las top 3 keywords: {', '.join(top_keywords)}"
        )
        
        # Keywords de baja competencia
        low_comp = [kw for kw in keywords if kw.get('competition', 1) < 0.3]
        if low_comp:
            recommendations.append(
                f"Aprovechar {len(low_comp)} keywords de baja competencia para wins rápidas"
            )
        
        # Long-tail opportunities
        long_tail = [kw for kw in keywords if len(kw.get('keyword', '').split()) >= 4]
        if long_tail:
            recommendations.append(
                f"Explorar {len(long_tail)} oportunidades long-tail para tráfico específico"
            )
        
        # Trending keywords
        trending = [kw for kw in keywords if kw.get('trend_score', 0) > 70]
        if trending:
            recommendations.append(
                f"Actuar rápido en {len(trending)} keywords con alta tendencia"
            )
        
        return recommendations[:5]  # Máximo 5 recomendaciones
    
    def generate_dashboard_data(self, keywords: List[Dict]) -> Dict:
        """Genera datos para dashboard de Streamlit"""
        if not keywords:
            return {}
        
        # Métricas generales
        total_keywords = len(keywords)
        avg_score = sum(kw.get('score', 0) for kw in keywords) / total_keywords
        high_potential = len([kw for kw in keywords if kw.get('score', 0) > 70])
        
        # Distribución por fuente
        sources = {}
        for kw in keywords:
            source = kw.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        # Top keywords por categoría
        by_category = {}
        for kw in keywords:
            category = self._categorize_keyword(kw.get('score', 0))
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(kw)
        
        return {
            'total_keywords': total_keywords,
            'avg_score': avg_score,
            'high_potential_count': high_potential,
            'sources_distribution': sources,
            'categories_distribution': by_category,
            'top_10': keywords[:10]
        }