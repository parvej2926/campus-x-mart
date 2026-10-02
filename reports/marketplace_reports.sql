-- Reporting queries for marketplace administration and analytics

-- 1. Total listing count by category
SELECT category, COUNT(*) AS total_listings
FROM items
GROUP BY category
ORDER BY total_listings DESC;

-- 2. Recently sold items summary
SELECT i.item_id, i.name, o.agreed_price, o.updated_at
FROM orders o
JOIN items i ON i.item_id = o.item_id
WHERE o.status = 'COMPLETED'
ORDER BY o.updated_at DESC;

-- 3. Top rated products
SELECT i.item_id, i.name, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(r.review_id) AS review_count
FROM items i
LEFT JOIN reviews r ON r.item_id = i.item_id
GROUP BY i.item_id, i.name
ORDER BY avg_rating DESC NULLS LAST;

-- 4. Seller overview
SELECT u.user_id, u.username, COUNT(i.item_id) AS listings_count
FROM users u
LEFT JOIN items i ON i.seller_id = u.user_id
GROUP BY u.user_id, u.username
ORDER BY listings_count DESC;
