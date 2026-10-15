# EDGAR-lxml-elt

[![Data source: SEC EDGAR](https://img.shields.io/badge/data%20source-SEC%20EDGAR-003366)](https://www.sec.gov/edgar/search/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![edgartools](https://img.shields.io/badge/built%20with-edgartools-2a78d6)](https://github.com/dgunning/edgartools)

An end-to-end pipeline that answers two questions: **which stocks are insiders cluster-buying right now**, and **do insider buys actually beat the market?**

![Annual revenue and net margin for Apple, Alphabet, Tesla, NVIDIA, BlackRock and Oracle, from XBRL financials](assets/revenue-and-net-margin.jpg)

## Data source

| Data | Where from | Updates |
|---|---|---|
| Insider trades (Forms 3, 4, 5) | [SEC insider transactions data sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets) | Quarterly |
| Financial statements (10-K, 10-Q) | [SEC financial statement data sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) | Quarterly |
| Ticker list (CIK ↔ ticker) | [SEC company_tickers_exchange.json](https://www.sec.gov/files/company_tickers_exchange.json) | Daily |
| Daily stock prices | Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Daily |

SEC data is public domain. Requests follow the SEC's
[fair access policy](https://www.sec.gov/os/accessing-edgar-data) (declared User-Agent, at most 10 requests/second).
Yahoo Finance data is for personal and educational use.

## How it works

1. **Extract** – download new SEC filings and stock prices.
2. **Land** – save the raw files in RustFS, untouched.
3. **Load** – add the new files to the bronze tables in ClickHouse.
4. **Transform** – dbt builds silver (typed, deduped) and gold (one table per question), then runs the data tests.
5. **Serve** – a Streamlit dashboard answers the two questions from gold.
6. **Repeat** – Prefect runs steps 1-4 every weekday at 6am.

Why these choices: see [DECISIONS.md](DECISIONS.md).

## Run it

You need [Docker](https://docs.docker.com/get-docker/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

1. **Get the code**
   ```bash
   git clone https://github.com/Grantalan/EDGAR-lxml-elt.git
   cd EDGAR-lxml-elt
   ```

2. **Add your settings** – copy the example, then put your name and email in `SEC_USER_AGENT`
   (SEC blocks requests without it) and pick your own passwords.
   ```bash
   cp .env.example .env
   ```

3. **Start the storage** (RustFS + ClickHouse)
   ```bash
   docker compose up -d rustfs clickhouse
   ```

4. **Load all the history** – one time only. Downloads ~20 GB; takes about 30 minutes on a good connection.
   ```bash
   uv run python scripts/form_345.py
   uv run python scripts/xbrl.py
   uv run python scripts/yf_prices.py
   uv run python scripts/load_bronze.py
   uv run dbt build --project-dir src/edgar_etl_s3/pipeline/transform --profiles-dir src/edgar_etl_s3/pipeline/transform
   ```

5. **Start everything** (Prefect, the daily pipeline, the dashboard)
   ```bash
   docker compose up -d
   ```
   - Dashboard: http://localhost:8501
   - Prefect runs: http://localhost:4200 (the pipeline runs every weekday at 6am Central)

Run it once by hand any time: `uv run python -m edgar_etl_s3.pipeline.flow`
