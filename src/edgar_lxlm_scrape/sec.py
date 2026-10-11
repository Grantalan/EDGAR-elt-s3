"""Shared helpers for every ingest script: download from SEC, land in RustFS."""

import os
import time

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


def already_landed(key):
    """True if this file is already in RustFS."""
    found = s3.list_objects_v2(Bucket=BUCKET, Prefix=key)
    return found["KeyCount"] > 0


def make_bucket():
    """Create the bucket the first time we run."""
    names = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if BUCKET not in names:
        s3.create_bucket(Bucket=BUCKET)
