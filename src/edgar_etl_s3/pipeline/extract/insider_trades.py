"""Land the insider trading quarters (Forms 3, 4, 5) SEC published since our last run.

The backfill (scripts/form_345.py) already landed every quarter since 2006, so
this only asks for quarters after the newest zip in RustFS.
"""

from tenacity import RetryError

from edgar_etl_s3.utils.sec import fetch, get_company_tickers, land, landed, quarters_since

# SEC moved the zips from 2026q2 on to this folder.
SOURCE = "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets"


def last_quarter():
    """The newest quarter in RustFS, e.g. insider_trades/2026q3_form345.zip -> 2026q3."""
    zips = [key for key in landed("insider_trades/") if key.endswith("_form345.zip")]
    return zips[-1].split("/")[-1][:6]


def extract():
    get_company_tickers()
    for quarter in quarters_since(last_quarter()):
        name = f"{quarter}_form345.zip"
        try:
            land(f"insider_trades/{name}", fetch(f"{SOURCE}/{name}"))
        except RetryError:
            # The quarter just ended and SEC hasn't published it yet. Next run will get it.
            print(f"skip {quarter} (not published yet)")
            return


if __name__ == "__main__":
    extract()
