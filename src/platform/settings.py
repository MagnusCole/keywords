from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from .exceptions_enterprise import ConfigError

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required to load configuration. Please install 'pyyaml'.") from e


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Deep merge two dicts (override wins).

    - Lists are replaced (not merged) by default to keep semantics predictable.
    - Scalars are overwritten.
    """
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _coerce_value(value: str) -> object:
    """Coerce string to bool/int/float/list where possible."""
    v = value.strip()
    low = v.lower()
    if low in {"true", "false"}:
        return low == "true"
    # numbers
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        pass
    # list (comma separated)
    if v.startswith("[") and v.endswith("]"):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    if "," in v:
        return [s.strip() for s in v.split(",") if s.strip()]
    return v


def parse_overrides(override_str: str | None) -> dict[str, object]:
    """Parse overrides like "a.b.c=x, d.e=y" into nested dict.

    Example: "run.target.filtered=400, run.geo=PE" -> {"run": {"target": {"filtered": 400}, "geo": "PE"}}
    """
    if not override_str:
        return {}
    result: dict[str, object] = {}
    pairs = [p.strip() for p in override_str.split(",") if p.strip()]
    for p in pairs:
        if "=" not in p:
            continue
        left, right = p.split("=", 1)
        keys = [k.strip() for k in left.split(".") if k.strip()]
        value = _coerce_value(right)
        cursor: dict[str, object] = result
        for k in keys[:-1]:
            if k not in cursor or not isinstance(cursor.get(k), dict):
                cursor[k] = {}
            cursor = cast(dict[str, object], cursor[k])
        cursor[keys[-1]] = value
    return result


class AppConfig:
    def __init__(self, data: dict[str, object]):
        self.data = data

    @property
    def run_id(self) -> str:
        return str(self.data.get("run_id", ""))


def load_config(config_path: str | os.PathLike[str], overrides: str | None = None) -> AppConfig:
    """Load YAML config and apply CLI overrides.

    - Reads YAML from `config_path`.
    - Applies overrides from string (a.b.c=x,...).
    - Returns AppConfig with merged dict.
    """
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}", config_path=str(path))

    try:
        with path.open("r", encoding="utf-8") as f:
            base: dict[str, object] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML format: {e}", config_path=str(path)) from e
    except Exception as e:
        raise ConfigError(f"Error reading config file: {e}", config_path=str(path)) from e

    try:
        ov = parse_overrides(overrides)
        merged = _deep_merge(base, ov)
    except Exception as e:
        raise ConfigError(f"Error processing overrides: {e}", config_path=str(path)) from e

    # add derived fields
    merged.setdefault("io", {})
    merged.setdefault("project", {})
    merged.setdefault("run", {})
    return AppConfig(data=merged)
