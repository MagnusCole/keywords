
# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import our modules
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
        st.markdown("### 📤 Sube tus semillas de keywords")

        # File uploader
        uploaded_file = st.file_uploader(
            "Selecciona un archivo CSV o TXT con tus keywords",
            type=['csv', 'txt'],
            help="El archivo debe contener una columna con keywords, una por línea"
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

            # Configuration options
            st.markdown("### ⚙️ Configuración del Análisis")

            col_a, col_b = st.columns(2)
            with col_a:
                geo = st.selectbox("País", ["PE", "MX", "CO", "CL", "AR"], index=0)
                language = st.selectbox("Idioma", ["es", "en"], index=0)

            with col_b:
                max_keywords = st.slider("Máximo keywords a analizar", 50, 500, 200)
                niche_name = st.text_input("Nombre del nicho", "Mi Nicho")

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