-- Do insider buys beat the market?
--
-- One row per open-market buy filing by an officer or director: the stock's
-- return 90 and 180 days after the filing date, next to SPY's over the same days.
-- Returns use adjusted close, so splits and dividends don't distort them.
-- Recent buys have NULL returns until enough days have passed.
{{ config(query_settings={'join_use_nulls': 1}) }}

with insider_filings as (
    select accession_number
    from {{ ref('silver_insider_owners') }}
    group by accession_number
    having max(is_officer or is_director) and not max(is_ten_percent_owner)
),

buys as (
    select
        f.accession_number                  as accession_number,
        f.ticker                            as ticker,
        f.filing_date                       as filing_date,
        f.filing_date + 90                  as day_90,
        f.filing_date + 180                 as day_180,
        'SPY'                               as spy,
        round(sum(t.shares * t.price))      as dollars_bought
    from {{ ref('silver_insider_trades') }} as t
    join {{ ref('silver_insider_filings') }} as f using (accession_number)
    where t.code = 'P'
      and t.price > 0
      and f.accession_number in (select accession_number from insider_filings)
    group by accession_number, ticker, filing_date
),

prices as (
    select ticker, trade_date, adj_close from {{ ref('silver_prices') }}
)

-- ASOF JOIN: the first trading day on or after each date (weekends, holidays).
select
    b.accession_number,
    b.ticker,
    b.filing_date,
    toYear(b.filing_date)                                   as filing_year,
    b.dollars_bought,
    round(100 * (s90.adj_close / s0.adj_close - 1), 2)      as return_90d,
    round(100 * (m90.adj_close / m0.adj_close - 1), 2)      as spy_return_90d,
    round(100 * (s180.adj_close / s0.adj_close - 1), 2)     as return_180d,
    round(100 * (m180.adj_close / m0.adj_close - 1), 2)     as spy_return_180d
from buys as b
asof left join prices as s0   on b.ticker = s0.ticker   and s0.trade_date   >= b.filing_date
asof left join prices as s90  on b.ticker = s90.ticker  and s90.trade_date  >= b.day_90
asof left join prices as s180 on b.ticker = s180.ticker and s180.trade_date >= b.day_180
asof left join prices as m0   on b.spy = m0.ticker      and m0.trade_date   >= b.filing_date
asof left join prices as m90  on b.spy = m90.ticker     and m90.trade_date  >= b.day_90
asof left join prices as m180 on b.spy = m180.ticker    and m180.trade_date >= b.day_180
where s0.adj_close > 0
