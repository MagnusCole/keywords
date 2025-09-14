# Keyword Finder 🔍

Herramienta automática de descubrimiento de keywords con **clustering inteligente** estilo SEMrush para AQXION.

## 🚀 Instalación

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

## 💻 Uso

```powershell
# Buscar keywords desde seeds con clustering automático
python main.py --seeds "marketing pymes" "curso seo"

# Exportar con reportes de clusters (CSV incluye cluster_report.csv y clusters_summary.csv)
python main.py --seeds "marketing digital" --export csv pdf

# Leer seeds desde archivo
python main.py --seeds-file seeds.txt

# Mostrar estadísticas de la base de datos
python main.py --stats

# Mostrar keywords ya guardadas
python main.py --existing --limit 20
```

## 🎯 Features

### **Core Pipeline**
- ✅ Google Autocomplete scraping (con variaciones)
- ✅ YouTube Autocomplete (sugerencias de vídeo) 
- ✅ Google Trends integration
- ✅ Semantic deduplication (85% similarity threshold)
- ✅ Enhanced volume/competition estimation

### **🧠 Clustering Inteligente (NUEVO)**
- ✅ **10 Cluster Patterns**: cursos_formacion, pymes_empresas, que_es_conceptos, como_hacer_howto, servicios_lima_local, redes_sociales, seo_posicionamiento, marketing_contenidos, herramientas_software, digital_online
- ✅ **Intent Classification**: Informational, Commercial, Transactional
- ✅ **Geographic Detection**: Detecta automáticamente términos locales (Perú, Lima)
- ✅ **Canonical Keywords**: Identifica keywords representativas por cluster
- ✅ **Opportunity Scoring**: `norm(volume) * (1 - competition) * trend_boost * cluster_focus`

### **📊 Export & Analytics**
- ✅ **cluster_report.csv**: Keywords nivel individual con cluster assignment
- ✅ **clusters_summary.csv**: Métricas por cluster con actionable notes
- ✅ Enhanced scoring automático (trend + volume + competition)
- ✅ Export CSV/PDF
- ✅ Base SQLite para persistencia
- ✅ Rate limiting inteligente

## 📊 Resultados de Ejemplo

### Clusters Summary
```csv
cluster_id,cluster_label,representative_kw,size,avg_score,opp_score_sum,top_intent,geo,notes
cursos_formacion,Cursos Formacion,como hacer curso seo,45,38.96,41014.5,commercial,PE,Landing 'Curso Marketing Digital Perú' + lead magnet
pymes_empresas,Pymes Empresas,marketing pymes online,16,37.9,14299.5,transactional,PE,Alta prioridad para conversión
que_es_conceptos,Que Es Conceptos,que es marketing pymes,6,47.43,5786.75,informational,PE,Content marketing potential
```

### Top Keywords
1. **como hacer marketing a mi negocio** - Score: 51.2 | Intent: Informational
2. **que es pyme peru** - Score: 50.9 | Intent: Informational | Geo: PE  
3. **que es seo en google** - Score: 49.2 | Intent: Informational

## 📁 Estructura del Proyecto

```
keyword-finder/
├── main.py                    # CLI principal
├── src/
│   ├── scrapers.py           # Google + YouTube scraping
│   ├── trends.py             # Google Trends integration
│   ├── scoring.py            # Scoring + Clustering inteligente
│   ├── exporters.py          # CSV/PDF + Cluster reports
│   └── database.py           # SQLite persistence
├── exports/                  # Reportes generados
│   ├── keyword_analysis_*.csv
│   ├── cluster_report_*.csv
│   └── clusters_summary_*.csv
└── tests/                    # Tests unitarios
```

## 🔧 Configuración

Las configuraciones se pueden ajustar en `KeywordFinder._load_default_config()`:

```python
{
    "trend_weight": 0.4,        # Peso de trends en scoring
    "volume_weight": 0.4,       # Peso de volumen en scoring
    "competition_weight": 0.2,  # Peso de competencia en scoring
    "top_keywords_limit": 20,   # Límite para reportes
    "request_delay_min": 1,     # Delay mínimo entre requests
    "request_delay_max": 3,     # Delay máximo entre requests
}
```

## 🧪 Testing

```powershell
# Ejecutar tests
pytest -q

# Lint y format
ruff check --fix .
black .
mypy src
```

## 📈 Roadmap

- [ ] **Machine Learning Clustering**: Implementar embeddings + K-means clustering
- [ ] **SERP Competitive Analysis**: Analizar primeros 10 resultados por keyword
- [ ] **Difficulty Estimation**: Algoritmo propio de dificultad SEO
- [ ] **API REST**: Endpoints para integración con otras herramientas
- [ ] **Streamlit Dashboard**: Interfaz web para análisis interactivo

## 🤝 Contribuir

1. Fork el repo
2. Crea branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -am 'Add nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crea Pull Request

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

**Desarrollado por AQXION** 🚀