-- Q4 (before): revenue and order count per product category.
-- Anti-pattern: a correlated CROSS APPLY re-scans the item fact and re-joins
-- dim_product once per distinct category (hundreds of executions), with
-- COUNT(DISTINCT order_id) forcing a sort inside every one of them.
-- Note: item-grain facts live in silver.order_items; dim_product supplies the
-- attributes (Gold keeps a single order-grain fact - see docs/architecture.md).

SELECT
    p.product_category_name,
    sub.category_revenue,
    sub.order_count
FROM (
    SELECT DISTINCT product_category_name
    FROM gold.dim_product
    WHERE product_category_name IS NOT NULL
) AS p
CROSS APPLY (
    SELECT
        SUM(x.price) AS category_revenue,
        COUNT(DISTINCT x.order_id) AS order_count
    FROM silver.order_items AS x
    INNER JOIN gold.dim_product AS px
        ON x.product_id = px.product_id
    WHERE
        px.product_category_name = p.product_category_name
        AND x.price > 0
) AS sub
ORDER BY sub.category_revenue DESC;
