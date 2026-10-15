# EDGAR-lxml-elt

[![Data source: SEC EDGAR](https://img.shields.io/badge/data%20source-SEC%20EDGAR-003366)](https://www.sec.gov/edgar/search/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)

An end-to-end pipeline that answers two questions: **which stocks are insiders cluster-buying right now**,
and **do insider buys actually beat the market?**

![Annual revenue and net margin for Apple, Alphabet, Tesla, NVIDIA, BlackRock and Oracle, from XBRL financials](assets/revenue-and-net-margin.jpg)

## Run it

You need [Docker](https://docs.docker.com/get-docker/) (give it **12 GB+ memory** and **40 GB disk** in
Docker Desktop settings) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

**1. Clone and configure**

```bash
git clone https://github.com/Grantalan/EDGAR-lxml-elt.git
cd EDGAR-lxml-elt
uv sync                  # create the environment (.venv/)
cp .env.example .env
```

Open `.env` and set `SEC_USER_AGENT` to your name and email.

**2. Start the storage**

```bash
docker compose up -d rustfs clickhouse
```

**3. Load all the history** (one time, ~20 GB, about 30 minutes)

```bash
./scripts/backfill.sh
```

**4. Start the dashboard and the daily pipeline**

```bash
docker compose up -d
```

| Open | What |
|---|---|
| http://localhost:8501 | Dashboard |
| http://localhost:4200 | Prefect: pipeline runs, logs, schedule (weekdays 6am Central) |

That's it. Every weekday the pipeline fetches only what's new, appends it, and rebuilds the dashboard tables.

## How it works

```
SEC + Yahoo ──► RustFS (raw files) ──► ClickHouse bronze ──► dbt silver ──► dbt gold ──► Streamlit
                └──────────────── Prefect, weekdays at 6am ────────────────┘
```

Why these choices: [DECISIONS.md](DECISIONS.md).

## Data source

| Data | Where from | Updates |
|---|---|---|
| Insider trades (Forms 3, 4, 5) | [SEC insider transactions data sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets) | Quarterly |
| Financial statements (10-K, 10-Q) | [SEC financial statement data sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) | Quarterly |
| Ticker list (CIK ↔ ticker) | [SEC company_tickers_exchange.json](https://www.sec.gov/files/company_tickers_exchange.json) | Daily |
| Daily stock prices | Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Daily |

SEC data is public domain; requests follow the SEC's [fair access policy](https://www.sec.gov/os/accessing-edgar-data)
(declared User-Agent, at most 10 requests/second). Yahoo Finance data is for personal and educational use.
