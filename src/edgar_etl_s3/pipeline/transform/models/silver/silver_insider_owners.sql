-- One row per insider per filing.
--
-- SEC packs roles into one text column ("Director,Officer"); split into true/false flags.
select
    ACCESSION_NUMBER                                    as accession_number,
    toUInt64OrNull(RPTOWNERCIK)                         as owner_cik,
    RPTOWNERNAME                                        as owner_name,
    RPTOWNER_TITLE                                      as title,
    RPTOWNER_RELATIONSHIP like '%Director%'             as is_director,
    RPTOWNER_RELATIONSHIP like '%Officer%'              as is_officer,
    RPTOWNER_RELATIONSHIP like '%TenPercentOwner%'      as is_ten_percent_owner
from {{ source('bronze', 'bronze_insider_reportingowner') }}
