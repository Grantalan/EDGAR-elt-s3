"""Download SEC's quarterly insider trading data (Forms 3, 4, 5) and save it to RustFS, untouched."""

from datetime import date

from tenacity import RetryError

from edgar_lxlm_scrape.sec import already_landed, fetch, land, make_bucket

# SEC's insider trading data sets start in 2006.
FIRST_YEAR = 2006


def get_insider_trades(year, quarter):
    """Every Form 3/4/5 insider trade filed in one quarter, as one zip file."""
    name = f"{year}q{quarter}_form345.zip"
    key = f"insider_trades/{name}"
    if already_landed(key):
        print(f"skip {key} (already landed)")
        return
    url = f"https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{name}"
    land(key, fetch(url))


def get_all_insider_trades():
    """Every quarter from 2006 until now. Quarters that haven't ended yet are never asked for."""
    today = date.today()
    current_quarter = (today.month - 1) // 3 + 1
    for year in range(FIRST_YEAR, today.year + 1):
        for quarter in [1, 2, 3, 4]:
            if (year, quarter) >= (today.year, current_quarter):
                return
            try:
                get_insider_trades(year, quarter)
            except RetryError:
                # The quarter just ended and SEC hasn't published it yet. Next run will get it.
                print(f"skip {year}q{quarter} (not published yet)")


def get_company_tickers():
    """Every ticker SEC knows about, with CIK, company name and exchange."""
    data = fetch("https://www.sec.gov/files/company_tickers_exchange.json")
    land(f"company_tickers/{date.today()}.json", data)


def get_filings(cik, ticker):
    """A company's filing history (10-K, 10-Q, 8-K, Form 4, ...)."""
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    land(f"filings/{ticker}/{date.today()}.json", fetch(url))


if __name__ == "__main__":
    make_bucket()
    get_company_tickers()
    get_all_insider_trades()
