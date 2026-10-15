# Decisions

**By the end of this, I'll be able to answer _which stocks insiders are cluster-buying right now_
and _whether insider buys actually beat the market_ about every US public company since 2006.**

## 1. Source — SEC EDGAR + Yahoo Finance

| | |
|---|---|
| **Insider trades** | SEC [insider transactions data sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets): every Form 3/4/5, one zip per quarter |
| **Financials** | SEC [financial statement data sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets): every number in every 10-K/10-Q, one zip per quarter |
| **Ticker list** | SEC [`company_tickers_exchange.json`](https://www.sec.gov/files/company_tickers_exchange.json): CIK ↔ ticker, updated daily |
| **Prices** | Yahoo Finance via `yfinance`: daily OHLCV for ~7,700 Nasdaq/NYSE/CBOE tickers + SPY |
| **Terms** | SEC data is public domain; requests follow SEC's [fair access policy](https://www.sec.gov/os/accessing-edgar-data) (declared User-Agent, ≤10 req/s). Yahoo data is for personal/educational use. |

**Why:** insiders must report every trade in their own company's stock within two business days.
It's free, official, goes back 20 years, and answers a real investing question. SEC's bulk quarterly
files beat 4.5M individual filing requests.

**Trade-off:** the bulk files are quarterly, so insider data lags up to a quarter. A daily feed from
EDGAR's filing index would close the gap but means parsing ~1,000 XML filings a day.

## 2. Raw landing — RustFS

Every file lands untouched, keyed by date or quarter (`insider_trades/2026q3_form345.zip`,
`prices/daily/2026-10-13/batch_000.csv`), so a re-run never overwrites yesterday and any layer can be
rebuilt from raw. ~10 GB.

**Trade-off:** another service to run, but it's S3-compatible: the same code works on AWS S3.

## 3. Analytical store — ClickHouse

~300M bronze rows (189M XBRL numbers alone). ClickHouse reads straight out of the zips in RustFS
(`s3('…/2026q3_form345.zip :: SUBMISSION.tsv')`), so loading a file is one SQL statement, and it
handles concurrent readers and writers.

**Why not DuckDB:** one writer at a time means the dashboard would block `dbt build`, forcing a
separate serving copy; and a single file at this size is uncomfortable. **Why not Postgres:**
row-oriented, so scans and aggregates over hundreds of millions of rows are slow.

**Trade-off:** less familiar SQL dialect (`argMax`, `ASOF JOIN`, `Date32`), and the `Date` type stops
at 1970: pre-1970 prices silently collapsed until silver switched to `Date32`.

## 4. Transform + orchestration — dbt + Prefect

- **Bronze** is append-only. Every row keeps `source_file`, and the daily loader only inserts files
  not already in the table, so the 20-year backfill is never reprocessed.
- **Silver** (dbt): typed, deduped, renamed, one row per real thing. Views, except `silver_prices`, a
  table because its dedupe takes ~2 minutes and gold reads it many times.
- **Gold** (dbt): one table per question.
- **22+ dbt tests**: `not_null`, `unique`, `accepted_values`, `relationships`.
- **Prefect** runs extract → land → load → `dbt build` on weekdays at 6am Central, with retries on every
  network step. The pipeline runs in Docker next to RustFS and ClickHouse, so nothing depends on an
  open terminal.

**Trade-off:** dbt on ClickHouse needs `threads: 1` (parallel queries on one session are rejected).

## 5. Serving — Streamlit

Two views on the gold tables: the current cluster buys, and median return after insider buys vs SPY
by year. Code-first, reads ClickHouse directly (no driver plugin like Metabase needs), and runs as a
container alongside the rest.

**No publish step:** ClickHouse serves the dashboard while dbt writes, so there's no serving copy.

## What broke along the way

- **SEC moved its files.** From 2026q2 the insider zips live at a new URL. The old code treated the
  404s as "not published yet" and silently skipped two quarters. The extractor now uses the new path.
- **SEC's own data has gaps.** The 2013q1 XBRL zip has 1,029 numbers for 4 filings missing from its
  own `sub.txt`. The relationships test reports it as a warning rather than failing the pipeline.
- **Memory.** Deduping 27M prices with a sort ran ClickHouse out of memory; a `row_number()` window
  (the course's dedupe pattern) does it in seconds.
