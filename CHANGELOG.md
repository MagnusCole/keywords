# Changelog

## 1.0.0 - 2025-09-15

- Multi-geo schema with composite uniqueness (keyword, geo, language) and indices.
- CLI wrapper (`src/cli.py`) and packaging entrypoint fix.
- CSV export: rename derived category to `priority_bucket`.
- DB filters: geo, language, intent, source, data_source, last_seen_after; CLI `--filters`.
- Ads volumes: cache TTL with migration, exponential backoff, and invalid customer_id guard.
- Categorization: `intent` persisted; `intent_prob` heuristic added.
- Persist per-row weights: `trend_weight`, `volume_weight`, `competition_weight`, `data_source`.
- Runs table to track execution metrics.
- Dashboard: sidebar filters (geo/language/intent/cluster) and cluster drill-through.
- Smoke test for DB insert and CSV export.
- Tooling: Ruff per-file complexity ignores; mypy overrides for known third-party issues.
