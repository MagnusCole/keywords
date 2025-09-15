import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class KeywordExporter:
    """Exportador de keywords a diferentes formatos (CSV, PDF)"""

    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        logging.info(f"KeywordExporter initialized with export directory: {self.export_dir}")

    def export_to_csv(self, keywords: list[dict], filename: str | None = None) -> str:
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
                "rank",
                "keyword",
                "source",
                "score",
                "trend_score",
                "volume",
                "competition",
                "cluster_id",
                "cluster_label",
                "data_source",
                "last_seen",
                "priority_bucket",
            ]

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for i, keyword in enumerate(keywords, 1):
                    row = {
                        "rank": i,
                        "keyword": keyword.get("keyword", ""),
                        "source": keyword.get("source", ""),
                        "score": keyword.get("score", 0),
                        "trend_score": keyword.get("trend_score", 0),
                        "volume": keyword.get("volume", 0),
                        "competition": keyword.get("competition", 0),
                        "cluster_id": keyword.get("cluster_id", ""),
                        "cluster_label": keyword.get("cluster_label", ""),
                        "data_source": keyword.get("data_source", "heurístico"),
                        "last_seen": keyword.get("last_seen", ""),
                        "priority_bucket": self._categorize_keyword(keyword.get("score", 0)),
                    }
                    writer.writerow(row)

            logging.info(f"Exported {len(keywords)} keywords to CSV: {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return ""

    def export_to_pdf(
        self,
        keywords: list[dict],
        filename: str | None = None,
        title: str = "Keyword Research Report",
    ) -> str:
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
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.darkblue,
            )
            story.append(Paragraph(title, title_style))

            # Información del reporte
            info_text = f"""
            <b>Fecha de generación:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}<br/>
            <b>Total de keywords analizadas:</b> {len(keywords)}<br/>
            <b>Top keywords mostradas:</b> {min(20, len(keywords))}
            """
            story.append(Paragraph(info_text, styles["Normal"]))
            story.append(Spacer(1, 20))

            # Resumen ejecutivo
            if keywords:
                summary = self._generate_executive_summary(keywords[:20])
                story.append(Paragraph("<b>Resumen Ejecutivo</b>", styles["Heading2"]))
                story.append(Paragraph(summary, styles["Normal"]))
                story.append(Spacer(1, 20))

            # Tabla de top keywords
            if keywords:
                story.append(Paragraph("<b>Top 20 Keywords</b>", styles["Heading2"]))
                table_data = self._prepare_table_data(keywords[:20])
                table = Table(table_data)

                # Estilo de la tabla
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                story.append(table)
                story.append(Spacer(1, 20))

            # Análisis por categorías
            if keywords:
                story.append(Paragraph("<b>Análisis por Categorías</b>", styles["Heading2"]))
                category_analysis = self._analyze_categories(keywords)
                story.append(Paragraph(category_analysis, styles["Normal"]))
                story.append(Spacer(1, 20))

            # Recomendaciones
            story.append(Paragraph("<b>Recomendaciones</b>", styles["Heading2"]))
            recommendations = self._generate_recommendations(keywords[:20])
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles["Normal"]))

            # Generar PDF
            doc.build(story)

            logging.info(f"Exported PDF report: {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Error exporting to PDF: {e}")
            return ""

    def _prepare_table_data(self, keywords: list[dict]) -> list[list[str]]:
        """Prepara datos para la tabla del PDF"""
        headers = [
            "Rank",
            "Keyword",
            "Score",
            "Trend",
            "Volume",
            "Competition",
            "Source",
            "Data Source",
        ]
        table_data = [headers]

        for i, kw in enumerate(keywords, 1):
            row = [
                str(i),
                kw.get("keyword", "")[:30] + ("..." if len(kw.get("keyword", "")) > 30 else ""),
                f"{kw.get('score', 0):.1f}",
                f"{kw.get('trend_score', 0):.0f}",
                f"{kw.get('volume', 0):,}",
                f"{kw.get('competition', 0):.2f}",
                kw.get("source", "")[:15],
                kw.get("data_source", "heurístico")[:12],
            ]
            table_data.append(row)

        return table_data

    def _generate_executive_summary(self, keywords: list[dict]) -> str:
        """Genera resumen ejecutivo del análisis"""
        if not keywords:
            return "No se encontraron keywords para analizar."

        # Estadísticas básicas
        avg_score = sum(kw.get("score", 0) for kw in keywords) / len(keywords)
        high_score_count = len([kw for kw in keywords if kw.get("score", 0) > 70])
        avg_competition = sum(kw.get("competition", 0) for kw in keywords) / len(keywords)

        # Fuentes más productivas
        sources: dict[str, int] = {}
        for kw in keywords:
            source = kw.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        top_source = max(sources.items(), key=lambda x: x[1]) if sources else ("N/A", 0)

        summary = f"""
        El análisis reveló {len(keywords)} keywords de alto potencial con un score promedio de {avg_score:.1f}/100.
        Se identificaron {high_score_count} keywords excelentes (score > 70) que representan oportunidades prioritarias.
        El nivel promedio de competencia es de {avg_competition:.2f}, indicando un mercado {'competitivo' if avg_competition > 0.6 else 'moderado'}.
        La fuente más productiva fue '{top_source[0]}' con {top_source[1]} keywords relevantes.
        """

        return summary.strip()

    def _analyze_categories(self, keywords: list[dict]) -> str:
        """Analiza keywords por categorías de score"""
        categories: dict[str, int] = {
            "excelente": 0,  # 80-100
            "buena": 0,  # 60-79
            "promedio": 0,  # 40-59
            "baja": 0,  # 20-39
            "muy_baja": 0,  # 0-19
        }

        for kw in keywords:
            score = kw.get("score", 0)
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

    def _generate_recommendations(self, keywords: list[dict]) -> list[str]:
        """Genera recomendaciones basadas en el análisis"""
        if not keywords:
            return ["No hay datos suficientes para generar recomendaciones."]

        recommendations = []

        # Top 3 keywords
        top_keywords = [kw.get("keyword", "") for kw in keywords[:3]]
        recommendations.append(
            f"Priorizar contenido para las top 3 keywords: {', '.join(top_keywords)}"
        )

        # Keywords de baja competencia
        low_comp = [kw for kw in keywords if kw.get("competition", 1) < 0.3]
        if low_comp:
            recommendations.append(
                f"Aprovechar {len(low_comp)} keywords de baja competencia para wins rápidas"
            )

        # Long-tail opportunities
        long_tail = [kw for kw in keywords if len(kw.get("keyword", "").split()) >= 4]
        if long_tail:
            recommendations.append(
                f"Explorar {len(long_tail)} oportunidades long-tail para tráfico específico"
            )

        # Trending keywords
        trending = [kw for kw in keywords if kw.get("trend_score", 0) > 70]
        if trending:
            recommendations.append(f"Actuar rápido en {len(trending)} keywords con alta tendencia")

        return recommendations[:5]  # Máximo 5 recomendaciones

    def generate_dashboard_data(self, keywords: list[dict]) -> dict:
        """Genera datos para dashboard de Streamlit"""
        if not keywords:
            return {}

        # Métricas generales
        total_keywords = len(keywords)
        avg_score = sum(kw.get("score", 0) for kw in keywords) / total_keywords
        high_potential = len([kw for kw in keywords if kw.get("score", 0) > 70])

        # Distribución por fuente
        sources: dict[str, int] = {}
        for kw in keywords:
            source = kw.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        # Top keywords por categoría
        by_category: dict[str, list[dict[str, Any]]] = {}
        for kw in keywords:
            category = self._categorize_keyword(kw.get("score", 0))
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(kw)

        return {
            "total_keywords": total_keywords,
            "avg_score": avg_score,
            "high_potential_count": high_potential,
            "sources_distribution": sources,
            "categories_distribution": by_category,
            "top_10": keywords[:10],
        }

    def export_cluster_report(
        self, clusters: dict[str, list[dict]], filename: str | None = None
    ) -> str:
        """
        Exporta cluster_report.csv según el plan de mejora
        Una fila por keyword con información de cluster
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cluster_report_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            fieldnames = [
                "cluster_id",
                "cluster_label",
                "keyword",
                "intent",
                "canonical",
                "score",
                "volume",
                "competition",
                "opp_score",
                "source",
                "category",
                "geo",
                "last_seen",
            ]

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for cluster_id, cluster_keywords in clusters.items():
                    if not cluster_keywords:
                        continue

                    # Find canonical keyword (highest opportunity score)
                    canonical_kw = ""
                    max_opp_score = 0

                    for kw_data in cluster_keywords:
                        volume = kw_data.get("volume", 0)
                        competition = kw_data.get("competition", 0.5)
                        opp_score = volume * (1 - competition)

                        if opp_score > max_opp_score:
                            max_opp_score = opp_score
                            canonical_kw = kw_data.get("keyword", "")

                    # Write all keywords in cluster
                    for kw_data in cluster_keywords:
                        keyword = kw_data.get("keyword", "")
                        volume = kw_data.get("volume", 0)
                        competition = kw_data.get("competition", 0.5)
                        opp_score = volume * (1 - competition)

                        # Detect geography
                        geo = (
                            "PE"
                            if any(term in keyword.lower() for term in ["lima", "perú", "peru"])
                            else ""
                        )

                        row = {
                            "cluster_id": cluster_id,
                            "cluster_label": cluster_id.replace("_", " ").title(),
                            "keyword": keyword,
                            "intent": kw_data.get("intent", "informational"),
                            "canonical": "TRUE" if keyword == canonical_kw else "FALSE",
                            "score": kw_data.get("score", 0),
                            "volume": volume,
                            "competition": competition,
                            "opp_score": round(opp_score, 2),
                            "source": kw_data.get("source", ""),
                            "category": kw_data.get("category", ""),
                            "geo": geo,
                            "last_seen": kw_data.get("last_seen", ""),
                        }
                        writer.writerow(row)

            logging.info(f"Exported cluster report: {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Error exporting cluster report: {e}")
            return ""

    def export_clusters_summary(
        self, clusters: dict[str, list[dict]], filename: str | None = None
    ) -> str:
        """
        Exporta clusters_summary.csv según el plan de mejora
        Una fila por cluster con estadísticas agregadas
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clusters_summary_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            fieldnames = [
                "cluster_id",
                "cluster_label",
                "representative_kw",
                "size",
                "avg_score",
                "sum_score",
                "avg_volume",
                "avg_competition",
                "opp_score_sum",
                "top_intent",
                "geo",
                "notes",
            ]

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                cluster_summaries = []

                for cluster_id, cluster_keywords in clusters.items():
                    if not cluster_keywords:
                        continue

                    # Calculate statistics
                    size = len(cluster_keywords)
                    scores = [kw.get("score", 0) for kw in cluster_keywords]
                    volumes = [kw.get("volume", 0) for kw in cluster_keywords]
                    competitions = [kw.get("competition", 0.5) for kw in cluster_keywords]

                    avg_score = sum(scores) / size if size > 0 else 0
                    sum_score = sum(scores)
                    avg_volume = sum(volumes) / size if size > 0 else 0
                    avg_competition = sum(competitions) / size if size > 0 else 0.5

                    # Calculate opportunity scores
                    opp_scores = [
                        vol * (1 - comp) for vol, comp in zip(volumes, competitions, strict=False)
                    ]
                    opp_score_sum = sum(opp_scores)

                    # Find representative keyword (highest opportunity)
                    best_kw = ""
                    max_opp = 0
                    for i, kw_data in enumerate(cluster_keywords):
                        if opp_scores[i] > max_opp:
                            max_opp = opp_scores[i]
                            best_kw = kw_data.get("keyword", "")

                    # Most common intent
                    intents = [kw.get("intent", "informational") for kw in cluster_keywords]
                    top_intent = (
                        max(set(intents), key=intents.count) if intents else "informational"
                    )

                    # Geography detection
                    has_geo = any(
                        any(
                            term in kw.get("keyword", "").lower()
                            for term in ["lima", "perú", "peru"]
                        )
                        for kw in cluster_keywords
                    )
                    geo = "PE" if has_geo else ""

                    # Generate notes
                    notes = self._generate_cluster_notes(cluster_id, size, avg_volume, top_intent)

                    cluster_summary = {
                        "cluster_id": cluster_id,
                        "cluster_label": cluster_id.replace("_", " ").title(),
                        "representative_kw": best_kw,
                        "size": size,
                        "avg_score": round(avg_score, 2),
                        "sum_score": round(sum_score, 2),
                        "avg_volume": round(avg_volume, 0),
                        "avg_competition": round(avg_competition, 2),
                        "opp_score_sum": round(opp_score_sum, 2),
                        "top_intent": top_intent,
                        "geo": geo,
                        "notes": notes,
                    }

                    cluster_summaries.append(cluster_summary)

                # Sort by opportunity score (highest first)
                cluster_summaries.sort(key=lambda x: x["opp_score_sum"], reverse=True)

                # Write rows
                for summary in cluster_summaries:
                    writer.writerow(summary)

            logging.info(f"Exported clusters summary: {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Error exporting clusters summary: {e}")
            return ""

    def _generate_cluster_notes(
        self, cluster_id: str, size: int, avg_volume: float, intent: str
    ) -> str:
        """Generate actionable notes for cluster based on characteristics"""
        notes = []

        if cluster_id == "cursos_formacion":
            notes.append("Landing 'Curso Marketing Digital Perú' + lead magnet")
        elif cluster_id == "como_hacer_howto":
            notes.append("Guía pilar + cluster de subtemas")
        elif cluster_id == "servicios_lima_local":
            notes.append("Landing servicio local + testimonios")
        elif cluster_id == "marketing_contenidos":
            notes.append("Pilar + plantillas PDF")
        elif cluster_id == "seo_posicionamiento":
            notes.append("Landing SEO PYMES + casos de estudio")

        if intent == "transactional":
            notes.append("Alta prioridad para conversión")
        elif intent == "commercial":
            notes.append("Lead generation opportunity")
        elif intent == "informational" and avg_volume > 1000:
            notes.append("Content marketing potential")

        if size > 20:
            notes.append(f"Gran cluster ({size} keywords)")

        return " | ".join(notes) if notes else "Standard content approach"
