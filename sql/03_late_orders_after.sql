-- Q3 (after): identical result - late-ness is computed once during the Gold
-- build (fact_orders.arrived_late) and the query reads a single integer flag.
-- COUNT(*) equals COUNT(DISTINCT order_id) because Gold asserts one row per order.

SELECT
    cu.state,
    COUNT(*) AS late_orders,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS late_share_pct
FROM gold.fact_orders AS f
INNER JOIN gold.dim_customer AS cu
    ON f.customer_key = cu.customer_key
WHERE f.arrived_late = 1
GROUP BY cu.state
ORDER BY late_orders DESC;
