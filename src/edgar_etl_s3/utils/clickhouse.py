"""Shared helper for talking to ClickHouse, plus how ClickHouse reaches RustFS."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

CLICKHOUSE_URL = f"http://{os.getenv('CLICKHOUSE_HOST')}:{os.getenv('CLICKHOUSE_PORT')}/"
CLICKHOUSE_AUTH = (os.getenv("CLICKHOUSE_USER"), os.getenv("CLICKHOUSE_PASSWORD"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")

# ClickHouse runs inside Docker, so it reaches RustFS by its Docker name, not localhost.
RAW = f"{os.getenv('S3_INTERNAL_ENDPOINT')}/{os.getenv('S3_BUCKET')}"
S3_KEYS = f"'{os.getenv('S3_ACCESS_KEY')}', '{os.getenv('S3_SECRET_KEY')}'"


def run(sql):
    """Send one SQL statement to ClickHouse."""
    resp = requests.post(
        CLICKHOUSE_URL, params={"database": CLICKHOUSE_DB}, data=sql, auth=CLICKHOUSE_AUTH
    )
    if not resp.ok:
        raise RuntimeError(resp.text)
    return resp.text
