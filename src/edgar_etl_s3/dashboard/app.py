"""The dashboard: two questions about insider buying, answered from the gold tables.

Run it:  uv run streamlit run src/edgar_etl_s3/dashboard/app.py   -> http://localhost:8501
"""

import os

import clickhouse_connect
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Categorical slots 1 and 2 of the chart palette: insider buys vs the market.
INSIDERS, MARKET = "#2a78d6", "#eb6834"


@st.cache_data(ttl=3600)
def query(sql):
    """Run a query against ClickHouse and return a DataFrame (cached for an hour)."""
    client = clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST"),
        port=int(os.getenv("CLICKHOUSE_PORT")),
        username=os.getenv("CLICKHOUSE_USER"),
        password=os.getenv("CLICKHOUSE_PASSWORD"),
        database=os.getenv("CLICKHOUSE_DB"),
    )
    return client.query_df(sql)


st.set_page_config(page_title="Insider Buying", layout="wide")
st.title("Are insiders buying?")
st.caption("SEC Form 4 insider trades since 2006 and Yahoo Finance prices, refreshed every weekday.")

# --- Question 1 -------------------------------------------------------------
st.header("Which stocks are insiders cluster-buying right now?")
st.write("Companies where 3+ officers or directors bought on the open market in the last 90 days of filings.")

clusters = query("SELECT * FROM gold_insider_cluster_buys")
st.dataframe(
    clusters,
    hide_index=True,
    width="stretch",
    column_config={
        "ticker": "Ticker",
        "company_name": "Company",
        "insiders_buying": "Insiders buying",
        "dollars_bought": st.column_config.NumberColumn("Bought", format="$%,.0f"),
        "avg_buy_price": st.column_config.NumberColumn("Avg buy price", format="$%.2f"),
        "last_buy": "Last buy",
        "last_close": st.column_config.NumberColumn("Last close", format="$%.2f"),
        "price_date": "Price date",
        "pct_vs_insider_price": st.column_config.NumberColumn("Now vs insider price", format="%.1f%%"),
    },
)

# --- Question 2 -------------------------------------------------------------
st.header("Do insider buys beat the market?")
days = st.radio("Holding period after the filing", [90, 180], format_func=lambda d: f"{d} days", horizontal=True)

# Medians, not averages: a few penny stocks that 10x would drag an average far from the typical buy.
by_year = query(f"""
    SELECT
        filing_year                                         AS year,
        count()                                             AS buys,
        round(median(return_{days}d), 1)                    AS insider_buys,
        round(median(spy_return_{days}d), 1)                AS spy,
        round(100 * avg(return_{days}d > spy_return_{days}d), 1) AS pct_beating_spy
    FROM gold_insider_buy_returns
    WHERE return_{days}d IS NOT NULL
    GROUP BY year
    ORDER BY year
""")

overall = query(f"""
    SELECT
        count()                                             AS buys,
        round(median(return_{days}d - spy_return_{days}d), 1) AS median_edge,
        round(100 * avg(return_{days}d > spy_return_{days}d), 1) AS pct_beating_spy
    FROM gold_insider_buy_returns
    WHERE return_{days}d IS NOT NULL
""").iloc[0]

left, middle, right = st.columns(3)
left.metric("Insider buys measured", f"{int(overall.buys):,}")
middle.metric(f"Median {days}-day edge over SPY", f"{overall.median_edge:+.1f} pts")
right.metric("Buys that beat SPY", f"{overall.pct_beating_spy:.0f}%")

st.write(f"Median {days}-day return after an insider buy, next to SPY over the same days, by filing year (%).")
st.bar_chart(
    by_year.set_index("year")[["insider_buys", "spy"]].rename(columns={"insider_buys": "Insider buys", "spy": "SPY"}),
    color=[INSIDERS, MARKET],
    stack=False,
)

with st.expander("Table view"):
    st.dataframe(by_year, hide_index=True, width="stretch")
