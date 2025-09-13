# Keyword Finder 🔍

Herramienta automática de descubrimiento de keywords para AQXION.

## 🚀 Instalación

```bash
pip install -r requirements.txt
```

## 💻 Uso

```bash
# Buscar keywords desde seeds
python main.py --seeds "marketing pymes" "limpieza piscinas Lima"

# Exportar top 20 keywords
python main.py --seeds "marketing digital" --export csv,pdf

# Ejecutar análisis completo
python main.py --seeds "marketing pymes" --full-analysis
```

## 📊 Features

- ✅ Google Autocomplete scraping
- ✅ Google Trends integration  
- ✅ Scoring automático (trend + volume + competition)
- ✅ Export CSV/PDF
- ✅ Base SQLite para persistencia
- ✅ Rate limiting inteligente

## 📁 Estructura

```
keyword-finder/
├── src/
│   ├── database.py      # SQLite operations
│   ├── scrapers.py      # Google scrapers
│   ├── scoring.py       # Keyword scoring
│   └── exporters.py     # CSV/PDF exports
├── exports/             # Generated reports
├── main.py             # CLI entry point
└── requirements.txt
```

## 🎯 Output

- **CSV**: Todas las keywords con scores
- **PDF**: Top 20 keywords + recomendaciones
- **SQLite**: Histórico completo