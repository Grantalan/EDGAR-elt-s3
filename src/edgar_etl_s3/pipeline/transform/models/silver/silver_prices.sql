-- One row per ticker per trading day.
--
-- The daily downloads overlap on purpose so no day is ever missed, which repeats
-- some days. Only the daily part has duplicates, so only it gets deduped (newest
-- download wins); history rows are kept unless a daily file already has that day.
-- Deduping all 27M rows the same way works too, but takes ~2 minutes instead of seconds.
with ranked_daily as (
    select
        *,
        row_number() over (
            partition by Ticker, Date
            order by source_file desc
        ) as rn
    from {{ source('bronze', 'bronze_prices') }}
    where source_file like '%/daily/%'
),

daily as (
    select Ticker, Date, Open, High, Low, Close, `Adj Close`, Volume
    from ranked_daily
    where rn = 1
),

all_days as (
    select * from daily
    union all
    select Ticker, Date, Open, High, Low, Close, `Adj Close`, Volume
    from {{ source('bronze', 'bronze_prices') }}
    where source_file not like '%/daily/%'
      and (Ticker, Date) not in (select Ticker, Date from daily)
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
from all_days
