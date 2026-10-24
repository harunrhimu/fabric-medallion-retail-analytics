-- Q2 (after): identical result - pre-aggregate the 2017 slice in one pass keyed
-- on date_key (one row per customer), then join dimensions and take TOP 10.

WITH customer_2017 AS (
    SELECT
        f.customer_key,
        SUM(f.order_total) AS revenue,
        COUNT(*) AS order_count
    FROM gold.fact_orders AS f
    INNER JOIN gold.dim_date AS d
        ON f.date_key = d.date_key
    WHERE
        d.calendar_year = 2017
        AND f.order_status <> 'canceled'
    GROUP BY f.customer_key
)

SELECT TOP 10
    cu.customer_id,
    cu.state,
    cr.revenue,
    cr.order_count,
    cr.revenue / cr.order_count AS avg_order_value
FROM customer_2017 AS cr
INNER JOIN gold.dim_customer AS cu
    ON cr.customer_key = cu.customer_key
ORDER BY cr.revenue DESC;
