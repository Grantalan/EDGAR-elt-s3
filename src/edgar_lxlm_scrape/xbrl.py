"""Download SEC's XBRL financial statement data and save it to RustFS, untouched.

SEC publishes every number tagged in every 10-K and 10-Q as one zip per quarter
(the "Financial Statement Data Sets"). Each zip holds four tab-separated files:

    sub.txt  one row per filing: company, CIK, form, fiscal year/period, filed date
    num.txt  one row per number: tag (e.g. Revenues), period end, unit, value
    tag.txt  what each tag means: label, debit/credit, data type
    pre.txt  where each number sits: balance sheet, income statement, cash flow

That's the same shape as the insider trading zips, so bronze.py can read them
straight out of RustFS the same way.
"""

from __future__ import annotations

from datetime import date

from tenacity import RetryError

from edgar_lxlm_scrape.form_345 import already_landed, fetch, land, make_bucket

# SEC's financial statement data sets start in 2009.
FIRST_YEAR = 2009

SOURCE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"


def quarter_name(year: int, quarter: int) -> str:
    """SEC's name for one quarter's zip, e.g. 2026q3.zip."""
    return f"{year}q{quarter}.zip"


def landing_key(year: int, quarter: int) -> str:
    """Where one quarter lives in RustFS. bronze.py globs on xbrl/*.zip."""
    return f"xbrl/{quarter_name(year, quarter)}"


def finished_quarters(today: date) -> list[tuple[int, int]]:
    """Every (year, quarter) from 2009 up to the last one that has ended.

    SEC only publishes a quarter after it ends, so the current one is never asked for.
    """
    current = (today.year, (today.month - 1) // 3 + 1)
    return [
        (year, quarter)
        for year in range(FIRST_YEAR, today.year + 1)
        for quarter in [1, 2, 3, 4]
        if (year, quarter) < current
    ]


def get_quarter(year: int, quarter: int) -> bool:
    """Land one quarter's zip. Returns True if it was downloaded, False if skipped.

    Skips quarters already in RustFS, so re-running only fetches what's new.
    """
    key = landing_key(year, quarter)
    if already_landed(key):
        print(f"skip {key} (already landed)")
        return False
    try:
        data = fetch(f"{SOURCE}/{quarter_name(year, quarter)}")
    except RetryError:
        # The quarter just ended and SEC hasn't published it yet. Next run will get it.
        print(f"skip {year}q{quarter} (not published yet)")
        return False
    land(key, data)
    return True


def get_all_quarters(today: date | None = None) -> int:
    """Land every finished quarter we don't have yet. Returns how many were downloaded."""
    quarters = finished_quarters(today or date.today())
    return sum(get_quarter(year, quarter) for year, quarter in quarters)


if __name__ == "__main__":
    make_bucket()
    count = get_all_quarters()
    print(f"{count} new quarters of XBRL data landed")
