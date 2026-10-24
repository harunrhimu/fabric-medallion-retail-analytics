-- Q1 (before): monthly revenue for 2017 with the matching 2016 figure.
-- Anti-pattern: two independent scans of the fact table with YEAR()/MONTH()
-- applied to the timestamp column, so the integer date_key cannot be used and
-- the whole aggregation runs twice.

WITH prior_year AS (
    SELECT
        MONTH(f.purchase_ts) AS sale_month,
        SUM(f.order_total) AS revenue
    FROM gold.fact_orders AS f
    WHERE
        YEAR(f.purchase_ts) = 2016
        AND f.order_status <> 'canceled'
    GROUP BY MONTH(f.purchase_ts)
)

SELECT
    2017 AS sale_year,
    current_year.sale_month,
    current_year.revenue,
    prior_year.revenue AS revenue_prior_year
FROM (
    SELECT
        MONTH(f.purchase_ts) AS sale_month,
        SUM(f.order_total) AS revenue
    FROM gold.fact_orders AS f
    WHERE
        YEAR(f.purchase_ts) = 2017
        AND f.order_status <> 'canceled'
    GROUP BY MONTH(f.purchase_ts)
) AS current_year
LEFT JOIN prior_year
    ON current_year.sale_month = prior_year.sale_month
ORDER BY current_year.sale_month;
