-- One row per stock trade, typed.
--
-- code P = open-market buy, S = open-market sell. Blank prices (gifts, grants)
-- stay NULL instead of becoming 0, so they can't drag down an average.
select
    NONDERIV_TRANS_SK                                   as trade_id,
    ACCESSION_NUMBER                                    as accession_number,
    toDate32(parseDateTime64BestEffortOrNull(TRANS_DATE)) as trade_date,
    TRANS_CODE                                          as code,
    toFloat64OrNull(TRANS_SHARES)                       as shares,
    toFloat64OrNull(TRANS_PRICEPERSHARE)                as price,
    TRANS_ACQUIRED_DISP_CD                              as acquired_disposed,
    toFloat64OrNull(SHRS_OWND_FOLWNG_TRANS)             as shares_owned_after
from {{ source('bronze', 'bronze_insider_nonderiv_trans') }}
