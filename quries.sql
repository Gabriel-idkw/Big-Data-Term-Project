-- =====================================================================
-- UrbanCart Term Project — Phase 1: SQL Extraction
-- Run against: ecommerce.db
-- Schema notes:
--   customers(customer_id, name, email, signup_date, city, country, age, gender)
--   products(product_id, name, category, subcategory, unit_price, cost)
--   orders(order_id, customer_id, order_date, status, payment_method)
--   order_items(order_item_id, order_id, product_id, quantity, unit_price, discount)
--     -> negative `quantity` = a return line item (confirmed via data check)
--   reviews(review_id, product_id, customer_id, rating, review_date, review_text)
--   web_sessions(session_id, customer_id, session_date, device, duration_minutes, pages_viewed)
--   order_date range: 2022-01-02 to 2024-12-31
-- =====================================================================

-- Q1: Revenue, order count, and AOV by category, net of discounts and returns.
-- (unit_price * quantity * (1 - discount), excluding negative-quantity/return rows)
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id)                                              AS num_orders,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2)           AS net_revenue,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount))
          * 1.0 / COUNT(DISTINCT oi.order_id), 2)                           AS aov
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.quantity > 0
GROUP BY p.category
ORDER BY net_revenue DESC;


-- Q2: Top 20 customers by lifetime spend, with city and signup date.
SELECT
    c.customer_id,
    c.name,
    c.city,
    c.signup_date,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS lifetime_spend
FROM customers c
JOIN orders o       ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE oi.quantity > 0
GROUP BY c.customer_id, c.name, c.city, c.signup_date
ORDER BY lifetime_spend DESC
LIMIT 20;


-- Q3: Month-over-month revenue trend for the last 24 months (window function: LAG()).
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS ym,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE oi.quantity > 0
    GROUP BY ym
    ORDER BY ym DESC
    LIMIT 24
)
SELECT
    ym,
    ROUND(revenue, 2)                                            AS revenue,
    ROUND(LAG(revenue) OVER (ORDER BY ym), 2)                    AS prev_month_revenue,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY ym), 2)          AS mom_change
FROM monthly
ORDER BY ym;


-- Q4: Return rate by category (share of order_items rows with negative quantity).
SELECT
    p.category,
    ROUND(SUM(CASE WHEN oi.quantity < 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS return_rate
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY return_rate DESC;


-- Q5: Customers active in all of the last 3 calendar quarters (from 2024-04-01 onward).
WITH last3q AS (
    SELECT
        customer_id,
        strftime('%Y', order_date) || '-Q' ||
            ((CAST(strftime('%m', order_date) AS INTEGER) - 1) / 3 + 1) AS quarter
    FROM orders
    WHERE order_date >= '2024-04-01'
)
SELECT customer_id, COUNT(DISTINCT quarter) AS active_quarters
FROM last3q
GROUP BY customer_id
HAVING COUNT(DISTINCT quarter) = 3
ORDER BY customer_id;


-- Q6: Top 10 products by average rating, requiring at least 15 reviews.
SELECT
    p.product_id,
    p.name,
    p.category,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    COUNT(*)                AS num_reviews
FROM reviews r
JOIN products p ON r.product_id = p.product_id
GROUP BY p.product_id, p.name, p.category
HAVING COUNT(*) >= 15
ORDER BY avg_rating DESC
LIMIT 10;


-- Q7: Avg session duration & pages viewed by device, restricted to customers
-- who have made at least one purchase (EXISTS subquery against orders).
SELECT
    ws.device,
    ROUND(AVG(ws.duration_minutes), 2) AS avg_duration_minutes,
    ROUND(AVG(ws.pages_viewed), 2)     AS avg_pages_viewed
FROM web_sessions ws
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = ws.customer_id
)
GROUP BY ws.device;


-- Q8: RANK() of products by net revenue within each category.
SELECT
    p.category,
    p.product_id,
    p.name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue,
    RANK() OVER (
        PARTITION BY p.category
        ORDER BY SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) DESC
    ) AS rank_in_category
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.quantity > 0
GROUP BY p.category, p.product_id, p.name
ORDER BY p.category, rank_in_category;


-- Q9: Payment-method mix by country (share of orders per method, within country).
SELECT
    c.country,
    o.payment_method,
    COUNT(*) AS n,
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY c.country), 3) AS share
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.country, o.payment_method
ORDER BY c.country, share DESC;


-- Q10 (own question): Which category generates the highest gross margin (net of
-- discounts and returns) in each country? Leadership cares about this because
-- revenue by category (Q1) doesn't reveal where the actual profit is coming from --
-- a high-revenue category can still be a low-margin one once product cost is netted out.
SELECT
    c.country,
    p.category,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost) * (1 - oi.discount)), 2) AS gross_margin
FROM order_items oi
JOIN orders o     ON oi.order_id = o.order_id
JOIN customers c  ON o.customer_id = c.customer_id
JOIN products p   ON oi.product_id = p.product_id
WHERE oi.quantity > 0
GROUP BY c.country, p.category
ORDER BY c.country, gross_margin DESC;