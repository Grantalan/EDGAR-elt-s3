"""Land the daily stock prices Yahoo Finance published since our last run.

The backfill (scripts/yf_prices.py) landed every ticker's full history. This
downloads from the newest day we have up to today, into prices/daily/<today>/.
Overlapping days are fine; silver removes the duplicates.
"""

from datetime import date

import yfinance as yf

from edgar_etl_s3.utils.sec import BUCKET, get_tickers, land, landed, s3

BATCH_SIZE = 100


def last_day():
    """The newest day before today we have prices for: the latest daily folder, else the backfill."""
    days = [key.split("/")[2] for key in landed("prices/daily/")]
    days = [day for day in days if day < str(date.today())]
    if days:
        return max(days)
    history = s3.head_object(Bucket=BUCKET, Key="prices/history/_complete")
    return str(history["LastModified"].date())


def extract():
    start = last_day()
    tickers = get_tickers()
    print(f"{len(tickers)} tickers since {start}")
    for i in range(0, len(tickers), BATCH_SIZE):
        # Only a few days per ticker, so threads=True asks Yahoo for the batch in parallel.
        df = yf.download(
            tickers[i : i + BATCH_SIZE], start=start,
            group_by="ticker", auto_adjust=False, progress=False, threads=True,
        )
        # Yahoo gives one column group per ticker. Turn that into one row per ticker per day.
        df = df.stack(level=0, future_stack=True).reset_index().dropna(subset=["Close"])
        land(f"prices/daily/{date.today()}/batch_{i // BATCH_SIZE:03d}.csv", df.to_csv(index=False).encode())


if __name__ == "__main__":
    extract()
