"""The daily pipeline as one Prefect flow: extract what's new -> land in RustFS -> append to bronze.

Run it on a schedule:   docker compose up -d   (Prefect server + this flow, see docker-compose.yml)
Run it once by hand:    uv run python -m edgar_etl_s3.pipeline.flow

See runs, logs and retries at http://localhost:4200.
"""

import sys

from prefect import flow, get_run_logger, task
from prefect.schedules import Cron

from edgar_etl_s3.pipeline.load import load_bronze
from edgar_etl_s3.pipeline.extract import insider_trades, prices, xbrl


@task(retries=2, retry_delay_seconds=60)
def extract_insider_trades() -> None:
    """Today's SEC ticker list plus any Form 3/4/5 quarter published since the last run."""
    logger = get_run_logger()
    insider_trades.extract()
    logger.info("insider trades landed in RustFS")


@task(retries=2, retry_delay_seconds=60)
def extract_xbrl() -> None:
    """Any XBRL financial statement quarter published since the last run."""
    logger = get_run_logger()
    xbrl.extract()
    logger.info("xbrl landed in RustFS")


@task(retries=2, retry_delay_seconds=60)
def extract_prices() -> None:
    """Daily prices from Yahoo Finance since the last run."""
    logger = get_run_logger()
    prices.extract()
    logger.info("prices landed in RustFS")


@task
def load() -> None:
    """Append the newly landed files to the bronze tables in ClickHouse."""
    logger = get_run_logger()
    load_bronze.load()
    logger.info("bronze tables up to date in ClickHouse")


@flow(name="edgar-daily", log_prints=True)
def run_pipeline() -> None:
    """Source to bronze, in order. Each call below becomes a tracked task run."""
    logger = get_run_logger()
    extract_insider_trades()
    extract_xbrl()
    extract_prices()
    load()
    logger.info("pipeline complete")


if __name__ == "__main__":
    if sys.argv[1:] == ["serve"]:
        # Weekdays at 6am Central, after Yahoo has the previous day's close.
        run_pipeline.serve(name="edgar-daily", schedules=[Cron("0 6 * * 1-5", timezone="America/Chicago")])
    else:
        run_pipeline()
