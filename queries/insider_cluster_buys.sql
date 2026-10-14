WITH
buys AS (
    SELECT
        upper(s.ISSUERTRADINGSYMBOL)  AS ticker,
        any(s.ISSUERNAME)             AS company,
        uniqExact(o.RPTOWNERCIK)      AS insiders_buying,
        round(sum(toFloat64OrZero(t.TRANS_SHARES) * toFloat64OrZero(t.TRANS_PRICEPERSHARE))) AS dollars_bought,
        round(avgIf(toFloat64OrZero(t.TRANS_PRICEPERSHARE), toFloat64OrZero(t.TRANS_PRICEPERSHARE) > 0), 2) AS avg_buy_price,
        max(parseDateTimeBestEffortOrNull(t.TRANS_DATE)) AS last_buy
    FROM edgar.bronze_insider_nonderiv_trans t
    JOIN edgar.bronze_insider_submission     s USING ACCESSION_NUMBER
    JOIN edgar.bronze_insider_reportingowner o USING ACCESSION_NUMBER
    WHERE t.TRANS_CODE = 'P'                                  -- open-market purchase
      AND (o.RPTOWNER_RELATIONSHIP ILIKE '%officer%' OR o.RPTOWNER_RELATIONSHIP ILIKE '%director%')
      AND o.RPTOWNER_RELATIONSHIP NOT ILIKE '%tenpercent%'    -- drop VC funds / IPO buyers
      AND parseDateTimeBestEffortOrNull(s.FILING_DATE) >=
          (SELECT max(parseDateTimeBestEffortOrNull(FILING_DATE)) FROM edgar.bronze_insider_submission) - INTERVAL 90 DAY
    GROUP BY ticker
    HAVING insiders_buying >= 3 AND dollars_bought >= 250000
),
latest AS (
    SELECT Ticker AS ticker, argMax(toFloat64OrZero(Close), Date) AS last_close, max(Date) AS price_date
    FROM edgar.bronze_prices
    GROUP BY Ticker
)
SELECT b.*, round(l.last_close, 2) AS last_close, l.price_date,
       round(100 * (l.last_close / b.avg_buy_price - 1), 1) AS pct_vs_insider_price
FROM buys b
JOIN latest l USING ticker
ORDER BY insiders_buying DESC, dollars_bought DESC
LIMIT 20;
