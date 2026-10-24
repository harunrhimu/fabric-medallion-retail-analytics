-- Q4 (after): identical result - one join, one GROUP BY, no per-category
-- subquery. The optimizer builds a hash join over items and products and
-- aggregates in a single pass.

SELECT
    p.product_category_name,
    SUM(oi.price) AS category_revenue,
    COUNT(DISTINCT oi.order_id) AS order_count
FROM silver.order_items AS oi
INNER JOIN gold.dim_product AS p
    ON oi.product_id = p.product_id
WHERE
    p.product_category_name IS NOT NULL
    AND oi.price > 0
GROUP BY p.product_category_name
ORDER BY category_revenue DESC;
