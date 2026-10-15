#!/usr/bin/env bash
# One-time backfill: all history -> RustFS -> bronze -> silver + gold.
# Run from the repo root:  ./scripts/backfill.sh
set -euo pipefail

# dbt reads its connection settings from the environment, not from .env.
set -a; source .env; set +a

uv run python scripts/form_345.py      # insider trades, every quarter since 2006
uv run python scripts/xbrl.py          # financial statements, every quarter since 2009
uv run python scripts/yf_prices.py     # full daily price history
uv run python scripts/load_bronze.py   # RustFS -> ClickHouse bronze tables
uv run dbt build \
    --project-dir src/edgar_etl_s3/pipeline/transform \
    --profiles-dir src/edgar_etl_s3/pipeline/transform   # silver + gold + tests
