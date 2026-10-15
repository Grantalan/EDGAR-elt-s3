"""One-time backfill: all history -> RustFS -> bronze -> silver + gold.

Run it from the repo root:  uv run scripts/backfill.py
"""

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# dbt reads its connection settings from the environment, not from .env.
load_dotenv()

SCRIPTS = Path(__file__).parent
TRANSFORM = SCRIPTS.parent / "src" / "edgar_etl_s3" / "pipeline" / "transform"
DBT = Path(sys.executable).parent / "dbt"

STEPS = [
    [sys.executable, SCRIPTS / "form_345.py"],      # insider trades, every quarter since 2006
    [sys.executable, SCRIPTS / "xbrl.py"],          # financial statements, every quarter since 2009
    [sys.executable, SCRIPTS / "yf_prices.py"],     # full daily price history
    [sys.executable, SCRIPTS / "load_bronze.py"],   # RustFS -> ClickHouse bronze tables
    [DBT, "build", "--project-dir", TRANSFORM, "--profiles-dir", TRANSFORM],  # silver + gold + tests
]

for step in STEPS:
    subprocess.run(step, check=True)  # stops at the first step that fails
