-- One row per ticker, from SEC's newest ticker list.
--
-- The bridge between the sources: insider filings use the CIK, prices use the ticker.
select
    toUInt64(cik)   as cik,
    name            as company_name,
    ticker,
    exchange
from {{ source('bronze', 'bronze_company_tickers') }}
where source_file = (select max(source_file) from {{ source('bronze', 'bronze_company_tickers') }})
