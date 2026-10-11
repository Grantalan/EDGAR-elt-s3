"""The whole pipeline as one Prefect flow: extract -> land in RustFS -> load bronze.

Run it once:            uv run python -m pipeline.flow
Run it on a schedule:   uv run python -m pipeline.flow serve

Start the Prefect server first (uv run prefect server start) to see runs at
http://127.0.0.1:4200.
"""

import sys

from prefect import flow, get_run_logger, task

from edgar_lxlm_scrape import form_345, load_bronze, sec, xbrl, yf_prices


@task(retries=2, retry_delay_seconds=60)
def extract_insider_trades() -> None:
    """SEC's ticker list plus every quarterly Form 3/4/5 zip we don't have yet."""
    logger = get_run_logger()
    sec.make_bucket()
    form_345.get_company_tickers()
    form_345.get_all_insider_trades()
    logger.info("insider trades landed in RustFS")


@task(retries=2, retry_delay_seconds=60)
def extract_xbrl() -> int:
    """Every quarterly XBRL financial statement zip we don't have yet."""
    logger = get_run_logger()
    count = xbrl.get_all_quarters()
    logger.info(f"xbrl: {count} new quarters landed in RustFS")
    return count


@task(retries=2, retry_delay_seconds=60)
def extract_prices() -> None:
    """Daily prices from Yahoo Finance: full history the first time, last 5 days after."""
    logger = get_run_logger()
    yf_prices.get_all_prices()
    logger.info("prices landed in RustFS")


@task
def load() -> None:
    """Rebuild every bronze table in ClickHouse from what's in RustFS."""
    logger = get_run_logger()
    load_bronze.load_insider_trades()
    load_bronze.load_xbrl()
    load_bronze.load_company_tickers()
    load_bronze.load_prices()
    logger.info("bronze tables loaded in ClickHouse")


@flow(log_prints=True)
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
        # Weekdays at 6am, after Yahoo has the previous day's close.
        run_pipeline.serve(name="edgar-nightly", cron="0 6 * * 1-5")
    else:
        run_pipeline()
