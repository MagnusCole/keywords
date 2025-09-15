from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_pdf(output_path: str = "exports/google_ads_use_case.pdf") -> str:
    os.makedirs(Path(output_path).parent, exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4, title="Google Ads API Use Case")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleBold", fontSize=18, leading=22, spaceAfter=12))
    styles.add(
        ParagraphStyle(name="Heading", fontSize=14, leading=18, spaceBefore=12, spaceAfter=6)
    )
    styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="Mono", fontName="Courier", fontSize=9, leading=12))

    content = []

    # Header
    content.append(Paragraph("Keyword Finder – Google Ads API Use Case", styles["TitleBold"]))
    content.append(
        Paragraph(datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), styles["Mono"])
    )
    content.append(Spacer(1, 0.5 * cm))

    # Company and business model
    content.append(Paragraph("Company Name", styles["Heading"]))
    content.append(
        Paragraph("MagnusCole – Keyword Finder (Internal SEO/SEM tooling)", styles["Body"])
    )

    content.append(Paragraph("Business Model", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "We operate internal research and reporting tools to support our owned and operated "
                "web properties and campaigns. We do not offer Ads management as a service for third parties. "
                "Our tool is used exclusively by employees to research keyword opportunities, cluster terms, "
                "estimate demand, and generate internal reports."
            ),
            styles["Body"],
        )
    )

    # Tool access and usage
    content.append(Paragraph("Tool Access/Use", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "Access is limited to internal employees (marketing, SEO/SEM analysts). The tool runs locally "
                "or on company-managed machines. We generate CSV/PDF exports for sharing with internal stakeholders. "
                "No external clients or third parties are granted direct access to the tool."
            ),
            styles["Body"],
        )
    )

    # Tool design
    content.append(Paragraph("Tool Design", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "The application ingests seed keywords, scrapes suggestions, clusters them semantically, and scores "
                "opportunities. When configured, it calls Google Ads' Keyword Plan Idea Service to fetch average monthly "
                "search volumes, which are stored locally (SQLite/CSV) for reporting. A CLI orchestrator controls features "
                "like semantic clustering, geo/language targeting, and Ads volume retrieval."
            ),
            styles["Body"],
        )
    )

    # Data flow table
    content.append(Paragraph("Data Flow Summary", styles["Heading"]))
    table = Table(
        [
            ["Step", "Description"],
            [
                "Input",
                "Seed keywords provided via CLI or file; optional geo/language parameters (e.g., PE/es).",
            ],
            [
                "Enrichment",
                "Scrape suggestions; compute embeddings and semantic clusters; apply advanced scoring.",
            ],
            [
                "Ads Volumes (optional)",
                "Query Google Ads Keyword Plan Idea Service to retrieve avg monthly searches; cache results.",
            ],
            [
                "Storage",
                "Persist to SQLite/CSV with clusters, volumes, and scores; caches stored under cache/.",
            ],
            [
                "Reporting",
                "Export CSV and PDF reports for internal review and planning.",
            ],
        ],
        colWidths=[3 * cm, 13 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    content.append(table)
    content.append(Spacer(1, 0.5 * cm))

    # API services used
    content.append(Paragraph("API Services Called", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "Google Ads API: Keyword Plan Idea Service (to retrieve average monthly searches). "
                "Other Ads management endpoints are NOT used by this tool."
            ),
            styles["Body"],
        )
    )

    # Access and security
    content.append(Paragraph("Access & Security", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "Credentials are stored via environment variables (.env) on internal machines. The tool fails gracefully "
                "when Ads credentials are not provided. No external access is granted; exports are shared internally."
            ),
            styles["Body"],
        )
    )

    # Mockups / screenshots section (placeholders)
    content.append(Paragraph("Tool Mockups / Screenshots", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "Below are placeholders for the dashboard and report mockups. Replace these images with real screenshots "
                "from your environment prior to submission."
            ),
            styles["Body"],
        )
    )

    placeholder = Path("google_search.html")
    if placeholder.exists():
        # Not an image, but we can show a note
        content.append(
            Paragraph("Included file: google_search.html (sample output)", styles["Mono"])
        )
    else:
        content.append(Paragraph("[Placeholder: Dashboard Screenshot]", styles["Mono"]))
    content.append(Spacer(1, 0.25 * cm))
    content.append(Paragraph("[Placeholder: CSV Export Screenshot]", styles["Mono"]))

    # Closing
    content.append(PageBreak())
    content.append(Paragraph("Contact & Ownership", styles["Heading"]))
    content.append(
        Paragraph(
            (
                "This tool is owned and operated internally by MagnusCole. It is not accessible to third parties. "
                "All websites and data used with this tool are owned or managed by our company."
            ),
            styles["Body"],
        )
    )

    doc.build(content)
    return output_path


if __name__ == "__main__":
    path = generate_pdf()
    print(f"Generated: {path}")
