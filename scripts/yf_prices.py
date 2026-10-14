"""Backfill: every ticker's full daily price history from Yahoo Finance, saved to RustFS.

Run once. After this, the pipeline (pipeline/extract/prices.py) lands only the new days.
"""

import yfinance as yf

from edgar_etl_s3.utils.sec import already_landed, get_tickers, land

# How many tickers to ask Yahoo for at once.
BATCH_SIZE = 100

# Landed after the last history batch. If a run dies halfway, this file is missing,
# so the next run downloads the full history again. Not a .csv, so bronze skips it.
HISTORY_DONE = "prices/history/_complete"


def get_prices(tickers, batch_number):
    """Full daily price history for a batch of tickers, saved as one CSV."""
    df = yf.download(tickers, period="max", group_by="ticker", auto_adjust=False, progress=False, threads=False)

    # Yahoo gives one column group per ticker. Turn that into one row per ticker per day.
    df = df.stack(level=0, future_stack=True).reset_index().dropna(subset=["Close"])
    land(f"prices/history/batch_{batch_number:03d}.csv", df.to_csv(index=False).encode())


def get_all_prices():
    """Every ticker's full history, in batches, unless it's already landed."""
    if already_landed(HISTORY_DONE):
        print("skip prices/history (already landed)")
        return

    tickers = get_tickers()
    print(f"{len(tickers)} tickers")
    for i in range(0, len(tickers), BATCH_SIZE):
        get_prices(tickers[i : i + BATCH_SIZE], i // BATCH_SIZE)
    land(HISTORY_DONE, b"")


if __name__ == "__main__":
    get_all_prices()
