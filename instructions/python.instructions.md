# instructions.md — Python Best Practices for AI Agents

> **Objetivo**: que cualquier agente/servicio en Python que escribas sea **legible, predecible, testeable** y **fácil de desplegar**. Copia-pega estas reglas en cada repo.

---

## 0) Principios (siempre)

* **PEP 8** para estilo; **Black** formatea, **Ruff** lintea; tú no discutes estilos.
* **Tipos en todo** (PEP 484): funciones públicas, modelos de datos, retornos y excepciones.
* **Pequeño > grande**: módulos cortos, funciones de una sola responsabilidad.
* **Explícito > implícito**: nombres claros, evitar magia.
* **Errores nunca pasan en silencio**: captura y registra; si recuperas, deja huella.

---

## 1) Estructura mínima de proyecto

```
repo/
├─ src/
│  └─ pkg_name/
│     ├─ __init__.py
│     ├─ core.py
│     ├─ models.py
│     ├─ io.py
│     └─ settings.py
├─ tests/
│  └─ test_core.py
├─ pyproject.toml
├─ README.md
├─ .gitignore
└─ .env.example
```

**Reglas**

* Código productivo vive en `src/pkg_name`. Evita imports relativos frágiles.
* Tests con `pytest` en `tests/` espejando el árbol de `src/`.

---

## 2) `pyproject.toml` de batalla (formatter/linter/types/tests)

Ajusta `pkg_name` y versiones.

```toml
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pkg_name"
version = "0.1.0"
description = "AI agent component"
readme = "README.md"
requires-python = ">=3.11"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E","F","I","UP","B","N","S","C90"]
ignore = ["E203","W503"]
fix = true

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_return_any = true
no_implicit_optional = true
plugins = []

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-q --color=yes --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src/pkg_name"]

[tool.coverage.report]
fail_under = 85
skip_covered = true
show_missing = true
```

---

## 3) Entornos y dependencias

* Usa **venv** o **uv** para entornos reproducibles.
* Pinea dependencias de producción; separa `dev` (pytest, coverage, ruff, black, mypy).
* Exponer comandos en **Makefile** o **taskfile**:

```Makefile
setup: ## instalar deps
	python -m venv .venv && . .venv/bin/activate && pip install -U pip
	pip install -e .[dev]

fmt:	ruff check --fix . && black .

lint:	ruff check . && mypy src

test:	pytest -q

cov:	pytest -q --cov=src/pkg_name --cov-report=term-missing
```

---

## 4) Estilo y tipos

* Escribe **docstrings** concisos (Google o NumPy style).
* Siempre anota tipos en funciones públicas. Ejemplo:

```python
from typing import Iterable

def top_k(items: Iterable[int], k: int) -> list[int]:
    """Return the k largest integers from items."""
    return sorted(items, reverse=True)[:k]
```

* Modelado de datos: **Pydantic** para validación/serialización cuando interactúes con APIs/archivos.

```python
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str = Field(min_length=1)
```

---

## 5) Manejo de errores y logging

* No uses `print()` en prod. Usa `logging` estructurado.
* Un **logger por módulo** con `__name__` y formatos JSON-friendly.

```python
import logging
logger = logging.getLogger(__name__)

try:
    risky()
except TimeoutError as e:
    logger.warning("timeout", extra={"op": "risky", "err": str(e)})
    raise
```

Config mínima (arranque de app):

```python
import logging, sys
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

---

## 6) IO/Concurrencia

* CPU-bound → `multiprocessing`/C-extensions. I/O-bound → `asyncio`/`aiohttp`.
* **Regla**: no mezcles sync/async en la misma ruta caliente. Encapsula adaptadores.

```python
import asyncio, aiohttp

async def fetch_json(url: str) -> dict:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=10) as r:
            r.raise_for_status()
            return await r.json()
```

---

## 7) Testing

* Unit tests rápidos + pruebas de integración por módulo crítico.
* Usa **fixtures** y **parametrización** de `pytest`.

```python
import pytest
from pkg_name.core import top_k

@pytest.mark.parametrize("items,k,expected", [([1,3,2],2,[3,2]), ([5],1,[5])])
def test_top_k(items, k, expected):
    assert top_k(items, k) == expected
```

CI: ejecuta `fmt`, `lint`, `mypy`, `pytest`, `coverage` (umbral ≥ 85%).

---

## 8) Configuración y secretos

* Todas las credenciales vía **variables de entorno**. Provee `.env.example`.
* Centraliza en `settings.py` (pydantic Settings ayuda).

---

## 9) Seguridad y hardening

* Congela versiones, revisa vulnerabilidades (pip-audit, ruff security).
* Sanitiza entradas; valida siempre con tipos/modelos.
* Tiempo de espera y reintentos con **backoff exponencial**.

---

## 10) Observabilidad

* IDs de correlación por request/tarea.
* Métricas con `prometheus_client` cuando aplique.
* Logs estructurados (+ nivel por entorno).

---

## 11) Documentación

* README con: propósito, cómo correr, cómo testear, decisiones.
* Docsite con **MkDocs** o **Sphinx** para proyectos serios. Genera API docs desde docstrings.

---

## 12) Checklist de PR (copia en `.github/PULL_REQUEST_TEMPLATE.md`)

* [ ] Código formateado (`make fmt`)
* [ ] Lint limpio (`make lint`)
* [ ] Tipado estricto (`mypy src`)
* [ ] Tests pasan (`make test`) y cobertura ≥ 85% (`make cov`)
* [ ] Docstrings agregados/actualizados
* [ ] No secretos en el diff

---

## 13) Plantilla mínima de agente (CLI + core)

```python
# src/pkg_name/cli.py
from __future__ import annotations
import argparse
from .core import run_agent

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("prompt", help="instrucción para el agente")
    args = p.parse_args()
    result = run_agent(args.prompt)
    print(result)

if __name__ == "__main__":
    main()
```

```python
# src/pkg_name/core.py
from typing import Final

SYSTEM_PROMPT: Final[str] = (
    "Eres un agente disciplinado. Responde con pasos claros y JSON opcional."
)

def run_agent(prompt: str) -> str:
    """Entry-point puro para orquestar el comportamiento del agente.

    - Valida entrada
    - Llama proveedores (LLM/API) a través de adaptadores
    - Devuelve salida limpia
    """
    if not prompt.strip():
        raise ValueError("prompt vacío")
    # TODO: insertar llamada a proveedor LLM (adaptador)
    return f"[OK] {prompt}"
```

---

## 14) Adaptadores (patrón de puertos)

* Escribe adaptadores para LLMs/APIs que expongan **interfaces claras** y retornos tipados.
* Nunca mezcles lógica de negocio con llamadas HTTP.

---

## 15) Rendimiento

* Mide primero (profilers: `cProfile`, `py-spy`).
* Evita hotspots: parsing repetido, JSON gigantes sin streams, regex pesadas.
* Usa caches (`functools.lru_cache`) donde aplique.

---

## 16) Ejemplos de comandos de calidad

```
ruff check . --fix
black .
mypy src
pytest -q
pytest -q --cov=src/pkg_name --cov-report=term-missing
```

---

## 17) Qué NO hacer

* Prints en producción.
* `except Exception: pass`.
* Funciones de +50 líneas o con efectos ocultos.
* Mezclar sync/async sin límites claros.
* Subir `.env` o llaves a git.

---

## 18) Referencias rápidas (añade a tu README)

* Estilo: PEP 8 + Black + Ruff
* Tipos: typing + mypy (modo estricto)
* Tests: pytest + coverage
* Docs: MkDocs/Sphinx
* Validación: Pydantic
* Async: asyncio/aiohttp para IO-bound

---

**Licencia**: libre para copiar y modificar en todos tus repos.
