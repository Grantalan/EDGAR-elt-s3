-- One row per reported number: which filing, which line item, which period, what value.
--
-- Company-wide totals only. Segment breakdowns (revenue by region, ...) and
-- co-registrant figures are about half the rows and would double count.
select
    adsh,
    tag,
    toDate32(parseDateTime64BestEffortOrNull(ddate))    as period_end,
    toUInt8OrNull(qtrs)                                 as quarters,  -- 0 = point in time, 1 = quarter, 4 = year
    uom                                                 as unit,
    toFloat64OrNull(value)                              as value
from {{ source('bronze', 'bronze_xbrl_num') }}
where segments = '' and coreg = ''
