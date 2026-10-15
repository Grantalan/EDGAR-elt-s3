-- One row per financial filing (10-K, 10-Q, 20-F, ...).
--
-- Which company and which fiscal period each set of numbers belongs to.
-- SEC writes dates as text (20260930); they become real dates.
select
    adsh,
    toUInt64OrNull(cik)                                 as cik,
    name                                                as company_name,
    form,
    toDate32(parseDateTime64BestEffortOrNull(period))   as period_end,
    toUInt16OrNull(fy)                                  as fiscal_year,
    fp                                                  as fiscal_period,
    toDate32(parseDateTime64BestEffortOrNull(filed))    as filed_date
from {{ source('bronze', 'bronze_xbrl_sub') }}
