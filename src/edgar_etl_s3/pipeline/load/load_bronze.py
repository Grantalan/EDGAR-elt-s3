"""Append the new raw files in RustFS to the ClickHouse bronze tables.

The backfill (scripts/load_bronze.py) built every bronze table once from all of
RustFS. Each row remembers the file it came from in source_file, so this only
reads files that aren't in the table yet, and reads them with the table's own
columns. Nothing is rebuilt; the tables only grow.
"""

from edgar_etl_s3.utils.clickhouse import RAW, S3_KEYS, run
from edgar_etl_s3.utils.sec import BUCKET, landed

# Same tab-separated-with-quotes rule the backfill uses for XBRL.
XBRL_SETTINGS = "SETTINGS format_custom_field_delimiter = '\\t', format_custom_escaping_rule = 'CSV'"

INSIDER_FILES = [
    "SUBMISSION", "REPORTINGOWNER", "NONDERIV_TRANS", "NONDERIV_HOLDING",
    "DERIV_TRANS", "DERIV_HOLDING", "FOOTNOTES", "OWNER_SIGNATURE",
]
XBRL_FILES = ["sub", "num", "tag", "pre"]


def new_files(table, prefix, ending, inside=""):
    """RustFS files under prefix whose rows aren't in the table yet, as (key, source_file)."""
    loaded = set(run(f"SELECT DISTINCT source_file FROM {table}").splitlines())
    files = []
    for key in landed(prefix):
        source_file = f"{BUCKET}/{key}" + (f"::{inside}" if inside else "")
        if key.endswith(ending) and source_file not in loaded:
            files.append(key)
    return files


def columns(table):
    """The table's columns (minus source_file), so new files are read exactly like the old ones."""
    rows = run(f"""
        SELECT name, type FROM system.columns
        WHERE database = currentDatabase() AND table = '{table}' AND name != 'source_file'
        ORDER BY position FORMAT TSV
    """)
    return ", ".join(f"`{name}` {type_}" for name, type_ in (row.split("\t") for row in rows.splitlines()))


def append(table, prefix, ending, fmt, inside="", settings=""):
    """Append each new file under prefix to the table, one INSERT per file."""
    for key in new_files(table, prefix, ending, inside):
        path = f"{RAW}/{key}" + (f" :: {inside}" if inside else "")
        run(f"""
            INSERT INTO {table}
            SELECT *, _path AS source_file
            FROM s3('{path}', {S3_KEYS}, '{fmt}', '{columns(table)}')
            {settings}
        """)
        print(f"appended {key} -> {table}")


def load_company_tickers():
    """SEC's ticker list. The JSON is {"fields": [...], "data": [[cik, name, ticker, exchange], ...]}."""
    for key in new_files("bronze_company_tickers", "company_tickers/", ".json"):
        run(f"""
            INSERT INTO bronze_company_tickers
            SELECT row.1, row.2, row.3, row.4, _path
            FROM s3('{RAW}/{key}', {S3_KEYS}, 'JSONAsString')
            ARRAY JOIN JSONExtract(json, 'data', 'Array(Tuple(String, String, String, String))') AS row
        """)
        print(f"appended {key} -> bronze_company_tickers")


def load():
    for name in INSIDER_FILES:
        append(f"bronze_insider_{name.lower()}", "insider_trades/", "_form345.zip", "TSVRawWithNames", f"{name}.tsv")
    for name in XBRL_FILES:
        append(f"bronze_xbrl_{name}", "xbrl/", ".zip", "CustomSeparatedWithNames", f"{name}.txt", XBRL_SETTINGS)
    load_company_tickers()
    append("bronze_prices", "prices/", ".csv", "CSVWithNames")


if __name__ == "__main__":
    load()
