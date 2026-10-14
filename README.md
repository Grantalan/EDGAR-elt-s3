# EDGAR-elt-s3

[![Data source: SEC EDGAR](https://img.shields.io/badge/data%20source-SEC%20EDGAR-003366)](https://www.sec.gov/edgar/search/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![edgartools](https://img.shields.io/badge/built%20with-edgartools-2a78d6)](https://github.com/dgunning/edgartools)

This is going to be an end-to-end SEC filing monitor system to create investment advice.

![Annual revenue and net margin for Apple, Alphabet, Tesla, NVIDIA, BlackRock and Oracle, from XBRL financials](assets/revenue-and-net-margin.jpg)

## Data source

All data comes from the U.S. Securities and Exchange Commission's
[EDGAR](https://www.sec.gov/edgar/search/) system: Form 4 insider trades, 8-K events, 10-K XBRL financials,
13F-HR institutional holdings and Form D private offerings. Requests follow the SEC's
[fair access policy](https://www.sec.gov/os/accessing-edgar-data) (declared User-Agent, at most 10 requests/second).

## How it works

1. **Extract** – download new SEC filings and stock prices.
2. **Land** – save the raw files in RustFS, untouched.
3. **Load** – add the new files to the bronze tables in ClickHouse.
4. **Repeat** – Prefect runs steps 1-3 every weekday at 6am.

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
   ```

5. **Start the daily pipeline** (Prefect + the pipeline)
   ```bash
   docker compose up -d
   ```
   It runs every weekday at 6am Central. Watch runs at http://localhost:4200.

Run it once by hand any time: `uv run python -m edgar_etl_s3.pipeline.flow`
