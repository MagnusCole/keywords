# Guía de Contribución - Keyword Finder

¡Gracias por tu interés en contribuir al proyecto Keyword Finder! Esta guía te ayudará a entender cómo contribuir de manera efectiva.

## 🚀 Inicio Rápido

### 1. Configuración del Entorno de Desarrollo

```bash
# Clona el repositorio
git clone https://github.com/MagnusCole/keywords.git
cd keyword-finder

# Crea entorno virtual
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Instala dependencias de desarrollo
make dev-install

# Configura pre-commit hooks
pip install pre-commit
pre-commit install
```

### 2. Estructura del Proyecto

```
keyword-finder/
├── src/keyword_finder/          # Código fuente principal
│   ├── core/                    # Módulos core
│   ├── workflows/              # Workflows automatizados
│   ├── cli/                    # Interfaz de línea de comandos
│   ├── models/                 # Modelos de datos
│   └── utils/                  # Utilidades
├── scripts/                    # Scripts y herramientas
├── tests/                      # Tests unitarios
├── docs/                       # Documentación
└── config/                     # Archivos de configuración
```

## 📝 Estándares de Código

### Python Code Style
- **Black**: Formateo automático (línea 88 caracteres)
- **Ruff**: Linting y corrección automática
- **MyPy**: Type checking estático
- **PEP 8**: Estándares de estilo Python

### Commits
Usamos [Conventional Commits](https://conventionalcommits.org/):

```bash
feat: add new clustering algorithm
fix: resolve memory leak in scraper
docs: update API documentation
refactor: simplify workflow orchestration
test: add unit tests for scoring module
```

### Pre-commit Hooks
Los hooks de pre-commit se ejecutan automáticamente antes de cada commit:

```bash
# Ejecutar manualmente
pre-commit run --all-files

# Ver hooks disponibles
pre-commit run --help
```

## 🧪 Testing

### Ejecutar Tests
```bash
# Todos los tests
make test

# Tests con coverage
make test-cov

# Tests específicos
pytest tests/test_scoring.py -v
```

### Escribir Tests
```python
import pytest
from src.keyword_finder.core.scoring import KeywordScorer

class TestKeywordScorer:
    def test_score_calculation(self):
        scorer = KeywordScorer()
        result = scorer.calculate_score("test keyword")
        assert result > 0
        assert isinstance(result, float)
```

## 🔧 Desarrollo

### Comandos Útiles
```bash
# Verificar calidad del código
make quality

# Formatear código
make format

# Limpiar archivos temporales
make clean

# Ejecutar demo
make demo
```

### Debugging
```bash
# Ejecutar con debugger
python -m debugpy --listen 5678 --wait-for-client src/keyword_finder/core/main.py

# O usar VSCode debugger (F5)
```

## 📚 Documentación

### Actualizar Docs
```bash
# Generar documentación
make docs

# Servir docs localmente
make docs-serve
```

### Estilo de Documentación
```python
def calculate_score(keyword: str, volume: int) -> float:
    """
    Calculate keyword score based on volume and other factors.

    Args:
        keyword: The keyword to score
        volume: Search volume from Google Ads

    Returns:
        Calculated score between 0 and 100

    Raises:
        ValueError: If keyword is empty

    Example:
        >>> score = calculate_score("marketing digital", 1000)
        >>> print(f"Score: {score:.2f}")
        Score: 85.50
    """
```

## 🔄 Workflows

### Tipos de Contribuciones
- **🐛 Bug Fixes**: Corrección de errores
- **✨ Features**: Nuevas funcionalidades
- **📚 Documentation**: Mejoras en docs
- **🔧 Maintenance**: Refactoring y mejoras
- **🧪 Tests**: Nuevos tests o mejoras

### Proceso de PR
1. Fork el repositorio
2. Crea una branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit tus cambios: `git commit -m 'feat: add nueva funcionalidad'`
4. Push a la branch: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

### Checklist PR
- [ ] Tests pasan localmente
- [ ] Código formateado con Black
- [ ] Linting pasa (Ruff)
- [ ] Type checking pasa (MyPy)
- [ ] Documentación actualizada
- [ ] Cambios probados manualmente

## 🎯 Áreas de Contribución

### Alta Prioridad
- **Performance**: Optimización de algoritmos de clustering
- **Testing**: Más cobertura de tests
- **Documentation**: Guías de uso y API docs

### Media Prioridad
- **New Features**: Integraciones con nuevas APIs
- **UI/UX**: Mejoras en dashboards HTML
- **Internationalization**: Soporte multi-idioma

### Baja Prioridad
- **Tools**: Scripts de automatización
- **Examples**: Más casos de uso
- **CI/CD**: Mejoras en pipeline

## 📞 Soporte

### Canales
- **Issues**: Para bugs y feature requests
- **Discussions**: Para preguntas generales
- **Discord/Slack**: Para chat en tiempo real

### Reportar Bugs
Usa la plantilla de bug report con:
- Descripción clara del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Logs y screenshots si aplica

## 📋 Código de Conducta

- Sé respetuoso con otros contribuidores
- Mantén un lenguaje profesional
- Ayuda a mantener el proyecto inclusivo
- Reporta cualquier comportamiento inapropiado

## 🙏 Reconocimientos

¡Gracias a todos los contribuidores que hacen posible este proyecto!

---

**Happy coding! 🚀**