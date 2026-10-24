-- Q3 (before): late-arriving orders per state and their share of all late orders.
-- Anti-pattern: DATEDIFF evaluated on two timestamp columns for every row, a
-- redundant OR the optimizer must still evaluate, then COUNT(DISTINCT) before
-- the aggregation can produce a result.

SELECT
    cu.state,
    COUNT(DISTINCT f.order_id) AS late_orders,
    COUNT(DISTINCT f.order_id) * 100.0 / SUM(COUNT(DISTINCT f.order_id)) OVER () AS late_share_pct
FROM gold.fact_orders AS f
INNER JOIN gold.dim_customer AS cu
    ON f.customer_key = cu.customer_key
WHERE
    DATEDIFF(DAY, f.purchase_ts, f.delivered_ts)
    > DATEDIFF(DAY, f.purchase_ts, f.estimated_delivery_ts)
    OR f.delivered_ts > f.estimated_delivery_ts
GROUP BY cu.state
ORDER BY late_orders DESC;
