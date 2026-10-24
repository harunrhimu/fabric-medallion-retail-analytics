-- Q2 (before): top 10 customers by 2017 revenue, with order count and AOV.
-- Anti-pattern: a correlated CROSS APPLY runs two subqueries for every customer
-- in dim_customer (~95k evaluations), and YEAR() inside the subquery prevents
-- the scan from seeking on date_key. Sorting all of that to return 10 rows.

SELECT TOP 10
    cu.customer_id,
    cu.state,
    sub.revenue,
    sub.order_count,
    sub.revenue / sub.order_count AS avg_order_value
FROM gold.dim_customer AS cu
CROSS APPLY (
    SELECT
        SUM(f.order_total) AS revenue,
        COUNT(*) AS order_count
    FROM gold.fact_orders AS f
    WHERE
        f.customer_key = cu.customer_key
        AND f.order_status <> 'canceled'
        AND YEAR(f.purchase_ts) = 2017
) AS sub
ORDER BY sub.revenue DESC;
