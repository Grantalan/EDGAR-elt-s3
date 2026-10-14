"""Shared helpers for every ingest script: download from SEC, land in RustFS, see what's landed."""

import json
import os
import time
from datetime import date

import boto3
import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# SEC blocks requests that don't say who you are ("Name email").
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}

BUCKET = os.getenv("S3_BUCKET")
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    region_name="us-east-1",
)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=30))
def fetch(url: str) -> bytes:
    """Download a URL from SEC and return the raw bytes."""
    time.sleep(0.2)  # stay well under SEC's limit of 10 requests per second
    resp = httpx.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()          # 429/5xx -> raises -> tenacity retries
    return resp.content


def land(key, data):
    """Save raw bytes to RustFS exactly as they arrived."""
    s3.put_object(Bucket=BUCKET, Key=key, Body=data)
    print(f"landed s3://{BUCKET}/{key} ({len(data):,} bytes)")


# The ticker list: CIK, company name, ticker and exchange for every company SEC knows.
TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"

# Prices only for major exchanges (OTC stocks mostly have no usable history),
# plus SPY, the market benchmark every strategy gets compared against.
EXCHANGES = ["Nasdaq", "NYSE", "CBOE"]
BENCHMARKS = ["SPY"]


def get_company_tickers():
    """Land today's copy of SEC's ticker list."""
    land(f"company_tickers/{date.today()}.json", fetch(TICKERS_URL))


def get_tickers():
    """Every stock ticker on a major exchange, from SEC's ticker list."""
    data = json.loads(fetch(TICKERS_URL))
    tickers = [row[2] for row in data["data"] if row[3] in EXCHANGES]
    return sorted(set(tickers)) + BENCHMARKS


def already_landed(key):
    """True if this file is already in RustFS."""
    found = s3.list_objects_v2(Bucket=BUCKET, Prefix=key)
    return found["KeyCount"] > 0


def make_bucket():
    """Create the bucket the first time we run."""
    names = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if BUCKET not in names:
        s3.create_bucket(Bucket=BUCKET)


def landed(prefix):
    """Every key already in RustFS under a prefix, in name order."""
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix)
    return sorted(obj["Key"] for page in pages for obj in page.get("Contents", []))


def quarters_since(last):
    """Every finished quarter after `last`, e.g. "2026q1" -> ["2026q2", "2026q3"]."""
    today = date.today()
    current = (today.year, (today.month - 1) // 3 + 1)
    year, quarter = int(last[:4]), int(last[-1])
    quarters = []
    while True:
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
        if (year, quarter) >= current:
            return quarters
        quarters.append(f"{year}q{quarter}")
