-- Q1 (after): identical result - one scan filtered on the integer date_key,
-- aggregation once, prior-year figure from a single LAG window instead of a
-- second pass over the fact table.

WITH monthly AS (
    SELECT
        d.calendar_year AS sale_year,
        d.calendar_month AS sale_month,
        SUM(f.order_total) AS revenue
    FROM gold.fact_orders AS f
    INNER JOIN gold.dim_date AS d
        ON f.date_key = d.date_key
    WHERE
        d.calendar_year IN (2016, 2017)
        AND f.order_status <> 'canceled'
    GROUP BY d.calendar_year, d.calendar_month
),

yoy AS (
    SELECT
        sale_year,
        sale_month,
        revenue,
        LAG(revenue) OVER (PARTITION BY sale_month ORDER BY sale_year) AS revenue_prior_year
    FROM monthly
)

SELECT
    sale_year,
    sale_month,
    revenue,
    revenue_prior_year
FROM yoy
WHERE sale_year = 2017
ORDER BY sale_month;
