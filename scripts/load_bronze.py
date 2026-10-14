"""Load the raw files from RustFS into ClickHouse bronze tables, as-is.

ClickHouse reads straight out of RustFS (even inside the zip files), so each
table is one SQL statement. Every column is loaded as text; cleaning is silver's job.
"""

from tenacity import retry, stop_after_attempt, wait_exponential

from edgar_etl_s3.utils.clickhouse import RAW, S3_KEYS, run

# The files inside each quarterly insider trading zip. One bronze table each.
INSIDER_FILES = [
    "SUBMISSION",        # one row per filing: company, ticker, filing date
    "REPORTINGOWNER",    # who filed: name, CEO / director / 10% owner
    "NONDERIV_TRANS",    # stock bought and sold: shares, price, buy or sell
    "NONDERIV_HOLDING",  # stock held, no trade
    "DERIV_TRANS",       # options and warrants traded
    "DERIV_HOLDING",     # options and warrants held
    "FOOTNOTES",
    "OWNER_SIGNATURE",
]

# The files inside each quarterly XBRL zip (SEC's financial statement data sets),
# with their columns. SEC fixes these columns, so we name them instead of letting
# ClickHouse guess (2009q1 has headers but no rows, so there is nothing to guess from).
XBRL_FILES = {
    # one row per 10-K / 10-Q: company, CIK, form, fiscal year and period
    "sub": [
        "adsh", "cik", "name", "sic", "countryba", "stprba", "cityba", "zipba", "bas1", "bas2",
        "baph", "countryma", "stprma", "cityma", "zipma", "mas1", "mas2", "countryinc", "stprinc",
        "ein", "former", "changed", "afs", "wksi", "fye", "form", "period", "fy", "fp", "filed",
        "accepted", "prevrpt", "detail", "instance", "nciks", "aciks",
    ],
    # every tagged number: tag, period end, unit, value
    "num": ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value", "footnote"],
    # what each tag means
    "tag": ["tag", "version", "custom", "abstract", "datatype", "iord", "crdr", "tlabel", "doc"],
    # which statement each number appears on
    "pre": ["adsh", "report", "line", "stmt", "inpth", "rfile", "tag", "version", "plabel", "negating"],
}

# XBRL files are tab-separated, but a few values are wrapped in double quotes and
# contain tabs (e.g. a 2022q4 10-K's list of investments). Plain TSV splits those
# into extra columns, so read tabs as the separator and honour CSV-style quotes.
XBRL_SETTINGS = """
SETTINGS format_custom_field_delimiter = '\\t',
         format_custom_escaping_rule = 'CSV'
"""

# Read every column as text instead of letting ClickHouse guess types.
# 'union' merges columns across years, since SEC added columns over time.
TEXT_SETTINGS = """
SETTINGS input_format_tsv_use_best_effort_in_schema_inference = 0,
         input_format_csv_use_best_effort_in_schema_inference = 0,
         schema_inference_mode = 'union'
"""


# RustFS occasionally returns a one-off error (e.g. "bucket does not exist") while
# ClickHouse reads dozens of zips at once. CREATE OR REPLACE makes a retry safe;
# reraise=True shows the real ClickHouse error if every attempt fails.
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=30, max=120), reraise=True)
def load_table(table, select):
    """Rebuild a bronze table from scratch, so re-running is always safe."""
    run(f"CREATE OR REPLACE TABLE {table} ENGINE = MergeTree ORDER BY tuple() AS {select}")
    rows = run(f"SELECT count() FROM {table}").strip()
    print(f"loaded {table} ({int(rows):,} rows)")


def load_insider_trades():
    """One table per TSV file, across every quarterly zip."""
    for name in INSIDER_FILES:
        load_table(
            f"bronze_insider_{name.lower()}",
            f"""
            SELECT *, _path AS source_file
            FROM s3('{RAW}/insider_trades/*.zip :: {name}.tsv', {S3_KEYS}, 'TSVRawWithNames')
            {TEXT_SETTINGS}
            """,
        )


def load_xbrl():
    """One table per file, across every quarterly XBRL zip."""
    for name, columns in XBRL_FILES.items():
        structure = ", ".join(f"{column} String" for column in columns)
        load_table(
            f"bronze_xbrl_{name}",
            f"""
            SELECT *, _path AS source_file
            FROM s3('{RAW}/xbrl/*.zip :: {name}.txt', {S3_KEYS}, 'CustomSeparatedWithNames', '{structure}')
            {XBRL_SETTINGS}
            """,
        )


def load_company_tickers():
    """SEC's ticker list. The JSON is {"fields": [...], "data": [[cik, name, ticker, exchange], ...]}."""
    load_table(
        "bronze_company_tickers",
        f"""
        SELECT
            row.1 AS cik,
            row.2 AS name,
            row.3 AS ticker,
            row.4 AS exchange,
            _path AS source_file
        FROM s3('{RAW}/company_tickers/*.json', {S3_KEYS}, 'JSONAsString')
        ARRAY JOIN JSONExtract(json, 'data', 'Array(Tuple(String, String, String, String))') AS row
        """,
    )


def load_prices():
    """Daily prices from Yahoo Finance: the one-time history plus every daily update."""
    load_table(
        "bronze_prices",
        f"""
        SELECT *, _path AS source_file
        FROM s3('{RAW}/prices/**/*.csv', {S3_KEYS}, 'CSVWithNames')
        {TEXT_SETTINGS}
        """,
    )


if __name__ == "__main__":
    load_insider_trades()
    load_xbrl()
    load_company_tickers()
    load_prices()
