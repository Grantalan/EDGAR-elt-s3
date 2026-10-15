-- One row per ticker per trading day.
--
-- The daily downloads overlap on purpose so no day is ever missed, which repeats
-- some days. Keep the newest copy: daily files beat the history, newer days beat older.
-- A table, not a view: the dedupe takes ~2 minutes, and gold reads prices many times.
{{ config(materialized='table') }}

with ranked as (
    select
        *,
        row_number() over (
            partition by Ticker, Date
            order by source_file like '%/daily/%' desc, source_file desc
        ) as rn
    from {{ source('bronze', 'bronze_prices') }}
)

select
    Ticker                          as ticker,
    toDate32(Date)                  as trade_date,  -- Date32: plain Date stops at 1970
    toFloat64OrNull(Open)           as open,
    toFloat64OrNull(High)           as high,
    toFloat64OrNull(Low)            as low,
    toFloat64OrNull(Close)          as close,
    toFloat64OrNull(`Adj Close`)    as adj_close,
    toFloat64OrNull(Volume)         as volume
from ranked
where rn = 1
