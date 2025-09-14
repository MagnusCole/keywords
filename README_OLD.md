# Keyword Finder 🔍

Herramienta automática de descubrimiento de keywords para AQXION.

## 🚀 Instalación

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -U pip; pip install -r requirements.txt
```
# Keyword Finder 🔍

Herramienta automática de descubrimiento de keywords (Google Autocomplete + Trends), scoring y exportación.

## 🚀 Instalación

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

## 💻 Uso

```powershell
# Buscar keywords desde seeds
python main.py --seeds "marketing pymes" "limpieza piscinas Lima"

# Exportar top 20 keywords (CSV y PDF)
python main.py --seeds "marketing digital" --export csv pdf

# Leer seeds desde archivo
python main.py --seeds-file seeds.txt

# Mostrar estadísticas de la base de datos
python main.py --stats

# Mostrar keywords ya guardadas
python main.py --existing --limit 20
```

## � Features

- ✅ Google Autocomplete scraping (con variaciones)
- ✅ YouTube Autocomplete (sugerencias de vídeo)
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
│   ├── trends.py        # Google Trends integration
│   └── exporters.py     # CSV/PDF exports
├── tools/               # Utilidades locales de debug (no producción)
├── tests/               # Unit tests
├── exports/             # Reportes generados
├── main.py              # CLI entry point
├── requirements.txt     # Dependencias de runtime
├── requirements-dev.txt # Dependencias de desarrollo (opcional)
└── pyproject.toml       # Black/Ruff/Mypy/Pytest config
```

## 🧪 Desarrollo

- Herramientas configuradas en `pyproject.toml` (Black, Ruff, Mypy, Pytest)
- Tareas VS Code en `.vscode/tasks.json`:

```powershell
# Formatear y auto-fix de lint
Run Task: fmt

# Lint + tipos
Run Task: lint

# Tests
Run Task: test
```

## 🔐 Variables de entorno

- Copia `.env.example` a `.env` y ajusta los valores.
- `.env` está ignorado en git.

## 📈 Dashboard y Demos

- Dashboard (Streamlit):
	```powershell
	streamlit run dashboard.py
	```
- Demo local (sin scraping):
	```powershell
	python tools/demo.py
	```
- Utilidad de debug de Google (inspección HTML):
	```powershell
	python tools/debug_google.py
	```
