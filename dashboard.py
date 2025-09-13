#!/usr/bin/env python3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

from database import KeywordDatabase
from exporters import KeywordExporter

st.set_page_config(page_title="Keyword Finder Dashboard", page_icon="🔍", layout="wide")


class KeywordDashboard:
    def __init__(self):
        self.db = KeywordDatabase()
        self.exporter = KeywordExporter()

    def run(self):
        st.title("🔍 Keyword Finder Dashboard")
        st.markdown("---")

        # Sidebar para controles
        with st.sidebar:
            st.header("🎛️ Controles")

            # Filtros
            st.subheader("Filtros")
            min_score = st.slider("Score mínimo", 0, 100, 0)
            max_competition = st.slider("Competencia máxima", 0.0, 1.0, 1.0)

            # Límite de resultados
            limit = st.selectbox("Máximo resultados", [10, 20, 50, 100], index=1)

            # Actualizar datos
            if st.button("🔄 Actualizar datos"):
                st.cache_data.clear()

        # Obtener datos
        keywords = self._get_filtered_keywords(min_score, max_competition, limit)

        if not keywords:
            st.warning("No hay keywords que coincidan con los filtros.")
            return

        # Métricas principales
        self._show_main_metrics(keywords)

        # Gráficos
        col1, col2 = st.columns(2)

        with col1:
            self._show_score_distribution(keywords)

        with col2:
            self._show_sources_distribution(keywords)

        # Tabla de keywords
        self._show_keywords_table(keywords)

        # Export
        self._show_export_options(keywords)

    @st.cache_data
    def _get_filtered_keywords(self, min_score, max_competition, limit):
        filters = {"min_score": min_score, "limit": limit}
        keywords = self.db.get_keywords(**filters)

        # Filtrar por competencia
        filtered = [kw for kw in keywords if kw.get("competition", 1) <= max_competition]

        return filtered

    def _show_main_metrics(self, keywords):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Keywords", len(keywords))

        with col2:
            avg_score = sum(kw.get("score", 0) for kw in keywords) / len(keywords)
            st.metric("Score Promedio", f"{avg_score:.1f}")

        with col3:
            high_potential = len([kw for kw in keywords if kw.get("score", 0) > 70])
            st.metric("Alto Potencial (>70)", high_potential)

        with col4:
            avg_competition = sum(kw.get("competition", 0) for kw in keywords) / len(keywords)
            st.metric("Competencia Prom.", f"{avg_competition:.2f}")

    def _show_score_distribution(self, keywords):
        st.subheader("📊 Distribución de Scores")

        scores = [kw.get("score", 0) for kw in keywords]

        fig = px.histogram(
            x=scores,
            nbins=20,
            title="Distribución de Scores",
            labels={"x": "Score", "y": "Cantidad de Keywords"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    def _show_sources_distribution(self, keywords):
        st.subheader("🎯 Keywords por Fuente")

        sources = {}
        for kw in keywords:
            source = kw.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        if sources:
            fig = px.pie(
                values=list(sources.values()),
                names=list(sources.keys()),
                title="Distribución por Fuente",
            )
            st.plotly_chart(fig, use_container_width=True)

    def _show_keywords_table(self, keywords):
        st.subheader("📋 Top Keywords")

        # Convertir a DataFrame
        df_data = []
        for i, kw in enumerate(keywords[:50], 1):  # Limitar a 50 para rendimiento
            df_data.append(
                {
                    "Rank": i,
                    "Keyword": kw.get("keyword", ""),
                    "Score": f"{kw.get('score', 0):.1f}",
                    "Trend": f"{kw.get('trend_score', 0):.0f}",
                    "Volume": f"{kw.get('volume', 0):,}",
                    "Competition": f"{kw.get('competition', 0):.2f}",
                    "Source": kw.get("source", ""),
                }
            )

        df = pd.DataFrame(df_data)

        # Configurar colores basados en score
        def color_score(val):
            score = float(val)
            if score >= 80:
                return "background-color: #d4edda"  # Verde
            elif score >= 60:
                return "background-color: #fff3cd"  # Amarillo
            elif score >= 40:
                return "background-color: #f8d7da"  # Rojo claro
            else:
                return "background-color: #f5f5f5"  # Gris

        # Apply style to the Score column in a version-tolerant way
        try:
            styled_df = df.style.applymap(color_score, subset=["Score"])  # type: ignore[attr-defined]
        except Exception:
            styled_df = df.style.apply(
                lambda col: [color_score(v) for v in col], subset=["Score"]
            )  # noqa: E501
        st.dataframe(styled_df, use_container_width=True)

    def _show_export_options(self, keywords):
        st.subheader("📤 Exportar Resultados")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📄 Exportar a CSV"):
                csv_file = self.exporter.export_to_csv(keywords)
                st.success(f"CSV generado: {csv_file}")

        with col2:
            if st.button("📕 Exportar a PDF"):
                pdf_file = self.exporter.export_to_pdf(
                    keywords[:20], title="Keyword Research Report - Dashboard"
                )
                st.success(f"PDF generado: {pdf_file}")


def main():
    dashboard = KeywordDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
