-- Which stocks are insiders cluster-buying right now?
--
-- One row per company where 3+ officers or directors bought stock on the open
-- market in the last 90 days of filings, for $250K+ in total. Insiders sell for
-- many reasons but buy for one. 10% owners (funds) are left out on purpose.
-- A buy only counts if its price is within 2x of that day's close: foreign companies'
-- insiders buy local shares in local currency, which can't be compared to the US listing.
with insider_filings as (
    -- filings by an officer or director, not a 10% owner
    select accession_number, groupArray(owner_cik) as owners
    from {{ ref('silver_insider_owners') }}
    group by accession_number
    having max(is_officer or is_director) and not max(is_ten_percent_owner)
),

buys as (
    select
        f.ticker                                    as ticker,
        any(f.company_name)                         as company_name,
        uniqExactArray(i.owners)                    as insiders_buying,
        round(sum(t.shares * t.price))              as dollars_bought,
        round(sum(t.shares * t.price) / sum(t.shares), 2) as avg_buy_price,
        max(t.trade_date)                           as last_buy
    from {{ ref('silver_insider_trades') }} as t
    join {{ ref('silver_insider_filings') }} as f using (accession_number)
    join insider_filings as i using (accession_number)
    join {{ ref('silver_prices') }} as p on p.ticker = f.ticker and p.trade_date = t.trade_date
    where t.code = 'P'
      and t.price between p.close / 2 and p.close * 2
      and f.filing_date >= (select max(filing_date) from {{ ref('silver_insider_filings') }}) - 90
    group by ticker
    having insiders_buying >= 3 and dollars_bought >= 250000
),

latest_price as (
    select ticker, argMax(close, trade_date) as last_close, max(trade_date) as price_date
    from {{ ref('silver_prices') }}
    group by ticker
)

select
    b.*,
    round(p.last_close, 2)                              as last_close,
    p.price_date,
    round(100 * (p.last_close / b.avg_buy_price - 1), 1) as pct_vs_insider_price
from buys as b
join latest_price as p using (ticker)
order by insiders_buying desc, dollars_bought desc
