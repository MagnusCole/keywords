from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_premium_report(data, output_path, niche_name):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()

    # Premium color palette
    premium_blue = colors.HexColor('#003366')  # Deep navy blue
    premium_gray = colors.HexColor('#F5F5F5')  # Light gray background
    premium_dark = colors.HexColor('#2C2C2C')  # Dark gray for text
    
    # Custom styles with premium colors
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center
        textColor=premium_blue,
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Heading2"],
        fontSize=18,
        spaceAfter=20,
        textColor=premium_dark,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=12,
        textColor=premium_dark,
        fontName="Helvetica"
    )

    story = []

    # Title
    story.append(
        Paragraph(f"Reporte Premium de Oportunidades de Mercado: {niche_name}", title_style)
    )
    story.append(Spacer(1, 0.5 * inch))

    # Executive Summary
    story.append(Paragraph("Resumen Ejecutivo", subtitle_style))
    story.append(
        Paragraph(
            "Este reporte analiza las oportunidades de keywords en el nicho seleccionado, incluyendo volumen de búsqueda, competencia y tendencias.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    # Top Keywords Table
    if "keywords" in data:
        story.append(Paragraph("Top 50 Keywords", subtitle_style))
        table_data = [["Keyword", "Volumen", "Competencia", "Tendencia"]]
        for kw in data["keywords"][:50]:
            table_data.append(
                [
                    kw.get("keyword", ""),
                    kw.get("volume", 0),
                    kw.get("competition", ""),
                    kw.get("trend", ""),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), premium_blue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), premium_gray),
                    ("TEXTCOLOR", (0, 1), (-1, -1), premium_dark),
                    ("GRID", (0, 0), (-1, -1), 1, premium_blue),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.5 * inch))

    # Clusters Section
    if "clusters" in data:
        story.append(Paragraph("Clusters Inteligentes", subtitle_style))
        for cluster in data["clusters"][:5]:  # Top 5 clusters
            story.append(Paragraph(f"Cluster: {cluster.get('name', '')}", styles["Heading3"]))
            story.append(
                Paragraph(f"Keywords: {', '.join(cluster.get('keywords', []))}", body_style)
            )
            story.append(Spacer(1, 0.25 * inch))

    # Trends
    story.append(Paragraph("Análisis de Tendencias", subtitle_style))
    story.append(
        Paragraph(
            "Basado en datos históricos, se identifican patrones de crecimiento en búsquedas relacionadas.",
            body_style,
        )
    )

    doc.build(story)


# Example usage
if __name__ == "__main__":
    # Sample data structure
    sample_data = {
        "keywords": [
            {
                "keyword": "marketing digital",
                "volume": 10000,
                "competition": "Alta",
                "trend": "Creciente",
            },
            # Add more...
        ],
        "clusters": [
            {"name": "SEO Básico", "keywords": ["seo", "optimización web"]},
            # Add more...
        ],
    }
    create_premium_report(sample_data, "templates/sample_report.pdf", "Marketing Digital Perú")
