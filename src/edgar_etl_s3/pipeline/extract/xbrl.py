"""Land the XBRL financial statement quarters SEC published since our last run.

The backfill (scripts/xbrl.py) already landed every quarter since 2009, so this
only asks for quarters after the newest zip in RustFS.
"""

from tenacity import RetryError

from edgar_etl_s3.utils.sec import fetch, land, landed, quarters_since

SOURCE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"


def last_quarter():
    """The newest quarter in RustFS, e.g. xbrl/2026q3.zip -> 2026q3."""
    zips = [key for key in landed("xbrl/") if key.endswith(".zip")]
    return zips[-1].split("/")[-1][:6]


def extract():
    for quarter in quarters_since(last_quarter()):
        try:
            land(f"xbrl/{quarter}.zip", fetch(f"{SOURCE}/{quarter}.zip"))
        except RetryError:
            # The quarter just ended and SEC hasn't published it yet. Next run will get it.
            print(f"skip {quarter} (not published yet)")
            return


if __name__ == "__main__":
    extract()
