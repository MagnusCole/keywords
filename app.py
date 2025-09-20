
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import our modules
# Import our modules
from ai_assistant import create_ai_assistant, display_ai_response
from keyword_finder.core.main import KeywordFinder
from templates.report_template import create_premium_report

# Page configuration
st.set_page_config(
    page_title="Keyword Finder Pro - Análisis Premium",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium styling
st.markdown("""
<style>
    .main-header {
        color: #003366;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .subtitle {
        color: #2C2C2C;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    .premium-button {
        background-color: #003366;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
    }
    .success-message {
        background-color: #F5F5F5;
        color: #003366;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #003366;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">🔍 Keyword Finder Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Análisis profesional de oportunidades de keywords - Sin código requerido</p>', unsafe_allow_html=True)

    # Sidebar with premium branding
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/003366/FFFFFF?text=Keyword+Finder+Pro", width=200)
        st.markdown("### 🚀 Características Premium")
        st.markdown("- ✅ Análisis de volumen de búsqueda")
        st.markdown("- ✅ Clustering inteligente")
        st.markdown("- ✅ Tendencias de Google")
        st.markdown("- ✅ Reportes PDF profesionales")
        st.markdown("- ✅ Exportación CSV completa")

        st.markdown("---")
        st.markdown("### 💰 Precios")
        st.markdown("**Reporte Básico:** $97")
        st.markdown("**Reporte Premium:** $197")
        st.markdown("**Análisis Completo:** $297")

    # Main content
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🎯 Elige tu método de análisis")

        # Mode selection
        mode = st.radio(
            "Cómo quieres proporcionar tus keywords:",
            ["📤 Subir archivo", "✏️ Ingresar manualmente"],
            help="Elige cómo quieres proporcionar las keywords para el análisis",
            key="input_mode_radio"
        )

        keywords = []
        niche_name = "Mi Nicho"

        if mode == "📤 Subir archivo":
            st.markdown("### 📤 Sube tus semillas de keywords")

            # File uploader
            uploaded_file = st.file_uploader(
                "Selecciona un archivo CSV o TXT con tus keywords",
                type=['csv', 'txt'],
                help="El archivo debe contener una columna con keywords, una por línea",
                key="keyword_file_uploader"
            )

            if uploaded_file is not None:
                # Process uploaded file
                if uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    keywords = df.iloc[:, 0].tolist()  # Assume first column
                else:
                    # TXT file
                    content = uploaded_file.getvalue().decode('utf-8')
                    keywords = [line.strip() for line in content.split('\n') if line.strip()]

                st.success(f"✅ Cargadas {len(keywords)} keywords")

        else:  # Manual input mode
            st.markdown("### ✏️ Ingresa tus keywords manualmente")

            # Manual keyword input
            manual_keywords = st.text_area(
                "Escribe tus keywords (una por línea):",
                height=150,
                placeholder="marketing digital\nseo\ngoogle ads\nmarketing para pymes",
                help="Escribe cada keyword en una línea separada",
                key="manual_keywords_textarea"
            )

            if manual_keywords.strip():
                keywords = [line.strip() for line in manual_keywords.split('\n') if line.strip()]
                if keywords:
                    st.success(f"✅ {len(keywords)} keywords listas para analizar")
                    st.markdown("**Keywords detectadas:**")
                    st.write(", ".join(keywords[:10]) + ("..." if len(keywords) > 10 else ""))

        # Configuration options (only show if we have keywords)
        if keywords:
            st.markdown("### ⚙️ Configuración del Análisis")

            col_a, col_b = st.columns(2)
            with col_a:
                geo = st.selectbox("País", ["PE", "MX", "CO", "CL", "AR"], index=0, key="geo_select")
                language = st.selectbox("Idioma", ["es", "en"], index=0, key="language_select")

            with col_b:
                max_keywords = st.slider("Máximo keywords a analizar", 50, 500, 200, key="max_keywords_slider")
                niche_name = st.text_input("Nombre del nicho", "Mi Nicho", key="niche_name_input")

            # AI Enhancement Section
            st.markdown("### 🤖 Mejora con IA (Opcional)")
            use_ai = st.checkbox("🔥 Activar Asistente de IA con Grok", help="Usa IA para generar sugerencias adicionales y análisis avanzado", key="use_ai_checkbox")

            ai_assistant = None
            ai_api_key = ""

            if use_ai:
                st.info("💡 La IA te ayudará generando keywords relacionadas y estrategias de contenido")
                ai_api_key = st.text_input(
                    "API Key de OpenRouter",
                    type="password",
                    help="Ingresa tu API key de OpenRouter (se mantiene privada)",
                    placeholder="sk-or-v1-xxxxxxxxxxxxxxxx",
                    key="ai_api_key_input"
                )

                if ai_api_key:
                    try:
                        ai_assistant = create_ai_assistant(ai_api_key)
                        st.success("✅ Asistente de IA configurado correctamente")
                    except Exception as e:
                        st.error(f"❌ Error configurando IA: {e}")
                        ai_assistant = None
                else:
                    st.warning("⚠️ Ingresa tu API key para activar las funciones de IA")
                    ai_assistant = None

            # Analysis button
            if st.button("🚀 Generar Análisis Premium", type="primary", use_container_width=True):
                with st.spinner("🔍 Analizando keywords... Esto puede tomar unos minutos"):

                    # Create temporary directory for results
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Initialize KeywordFinder
                        finder = KeywordFinder()

                        # Run analysis
                        try:
                            results = finder.run_analysis(
                                seeds=keywords[:max_keywords],
                                geo=geo,
                                language=language,
                                output_dir=temp_dir
                            )

                            # Generate PDF report
                            pdf_path = os.path.join(temp_dir, f"{niche_name.replace(' ', '_')}_report.pdf")

                            # Prepare data for template
                            data = {
                                "keywords": results.get("keywords", []),
                                "clusters": results.get("clusters", [])
                            }

                            create_premium_report(data, pdf_path, niche_name)

                            # Display results
                            st.markdown("---")
                            st.markdown("## 📊 Resultados del Análisis")

                            # Download buttons
                            col1, col2 = st.columns(2)

                            with col1:
                                with open(pdf_path, "rb") as pdf_file:
                                    st.download_button(
                                        label="📄 Descargar Reporte PDF",
                                        data=pdf_file,
                                        file_name=f"{niche_name}_report.pdf",
                                        mime="application/pdf",
                                        use_container_width=True
                                    )

                            with col2:
                                # Create ZIP with all files
                                import zipfile
                                zip_path = os.path.join(temp_dir, f"{niche_name}_complete.zip")
                                with zipfile.ZipFile(zip_path, 'w') as zipf:
                                    for file in os.listdir(temp_dir):
                                        if file.endswith(('.csv', '.pdf')):
                                            zipf.write(os.path.join(temp_dir, file), file)

                                with open(zip_path, "rb") as zip_file:
                                    st.download_button(
                                        label="📦 Descargar Paquete Completo",
                                        data=zip_file,
                                        file_name=f"{niche_name}_complete.zip",
                                        mime="application/zip",
                                        use_container_width=True
                                    )

                            # Success message
                            st.markdown("""
                            <div class="success-message">
                                <h3>✅ ¡Análisis completado exitosamente!</h3>
                                <p>Tu reporte premium está listo para descargar. Incluye análisis detallado de keywords, clustering inteligente y tendencias de mercado.</p>
                            </div>
                            """, unsafe_allow_html=True)

                            # AI Enhancement Section (only if AI was enabled)
                            if use_ai and ai_assistant and ai_api_key:
                                st.markdown("---")
                                st.markdown("## 🤖 Análisis Avanzado con IA")

                                # AI Suggestions Tab
                                tab1, tab2, tab3 = st.tabs(["💡 Sugerencias de Keywords", "🎯 Análisis Competitivo", "📝 Ideas de Contenido"])

                                with tab1:
                                    st.markdown("### 🔍 Generando sugerencias de keywords relacionadas...")
                                    with st.spinner("Consultando IA..."):
                                        ai_response = ai_assistant.generate_keyword_suggestions(
                                            seed_keywords=keywords[:5],  # Use first 5 keywords as seeds
                                            niche=niche_name,
                                            country=geo
                                        )
                                        display_ai_response(ai_response, "Sugerencias de Keywords Generadas")

                                with tab2:
                                    st.markdown("### 🏆 Analizando estrategias competitivas...")
                                    with st.spinner("Analizando competencia..."):
                                        ai_response = ai_assistant.analyze_competition_strategy(
                                            keywords=keywords[:10],  # Analyze top 10 keywords
                                            niche=niche_name
                                        )
                                        display_ai_response(ai_response, "Análisis Competitivo Completado")

                                with tab3:
                                    st.markdown("### 📝 Generando ideas de contenido...")
                                    with st.spinner("Creando ideas creativas..."):
                                        # Generate content ideas for the top keyword
                                        if keywords:
                                            ai_response = ai_assistant.generate_content_ideas(
                                                keyword=keywords[0],
                                                niche=niche_name
                                            )
                                            display_ai_response(ai_response, "Ideas de Contenido Generadas")

                        except Exception as e:
                            st.error(f"❌ Error durante el análisis: {str(e)}")
                            st.info("💡 Asegúrate de que tus keywords sean relevantes y no excedan los límites de la API.")

        else:
            # Instructions when no file is uploaded
            st.info("👆 Sube un archivo con tus keywords para comenzar el análisis")

            st.markdown("### 📋 Formato del archivo:")
            st.markdown("- **CSV:** Una columna con keywords")
            st.markdown("- **TXT:** Una keyword por línea")
            st.markdown("- **Ejemplo:** marketing digital, seo, google ads")

if __name__ == "__main__":
    main()