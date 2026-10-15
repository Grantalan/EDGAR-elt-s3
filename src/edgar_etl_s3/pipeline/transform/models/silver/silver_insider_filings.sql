-- One row per Form 3/4/5 filing.
--
-- SEC writes dates as text (31-MAR-2026) and CIKs zero-padded; both become real types.
select
    ACCESSION_NUMBER                                    as accession_number,
    toDate32(parseDateTime64BestEffortOrNull(FILING_DATE)) as filing_date,
    DOCUMENT_TYPE                                       as form,
    toUInt64OrNull(ISSUERCIK)                           as cik,
    ISSUERNAME                                          as company_name,
    upper(trim(ISSUERTRADINGSYMBOL))                    as ticker
from {{ source('bronze', 'bronze_insider_submission') }}
