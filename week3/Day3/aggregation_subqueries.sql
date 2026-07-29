-- PART 1 — AGGREGATION BASICS

-- Q1. Total revenue generated per store
-- Logic: payment -> staff (staff works at a store) -> store
SELECT
    s.store_id,
    SUM(p.amount) AS total_revenue
FROM payment p
JOIN staff s ON p.staff_id = s.staff_id
GROUP BY s.store_id
ORDER BY s.store_id;

-- Q2. Average rental duration (in days) per film category
-- Logic: rental -> inventory -> film -> film_category -> category
-- Rental "duration" here = actual days the customer kept the film
--   (return_date - rental_date), not the film's default rental_duration column.
SELECT
    c.name AS category,
    ROUND(AVG(EXTRACT(EPOCH FROM (r.return_date - r.rental_date)) / 86400)::numeric, 2) AS avg_rental_days
FROM rental r
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f ON i.film_id = f.film_id
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
WHERE r.return_date IS NOT NULL
GROUP BY c.name
ORDER BY avg_rental_days DESC;

-- Q3. Number of rentals made each month
SELECT
    TO_CHAR(DATE_TRUNC('month', rental_date), 'YYYY-MM') AS rental_month,
    COUNT(*) AS total_rentals
FROM rental
GROUP BY DATE_TRUNC('month', rental_date)
ORDER BY DATE_TRUNC('month', rental_date);

-- Q4. Categories with more than 50 films (HAVING)
SELECT
    c.name AS category,
    COUNT(fc.film_id) AS film_count
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
GROUP BY c.name
HAVING COUNT(fc.film_id) > 50
ORDER BY film_count DESC;

-- PART 2 — SUBQUERY CHALLENGES

-- Q5. Customers who spent more than the average customer spend
-- Non-correlated scalar subquery in WHERE clause
SELECT
    c.customer_id,
    c.first_name,
    c.last_name,
    SUM(p.amount) AS total_spent
FROM customer c
JOIN payment p ON c.customer_id = p.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING SUM(p.amount) > (
    SELECT AVG(customer_total)
    FROM (
        SELECT SUM(amount) AS customer_total
        FROM payment
        GROUP BY customer_id
    ) AS customer_totals
)
ORDER BY total_spent DESC;

-- Q6. Film(s) with the highest rental rate in each category
-- Correlated subquery: inner query re-evaluated per outer category row
SELECT
    c.name AS category,
    f.title,
    f.rental_rate
FROM film f
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
WHERE f.rental_rate = (
    SELECT MAX(f2.rental_rate)
    FROM film f2
    JOIN film_category fc2 ON f2.film_id = fc2.film_id
    WHERE fc2.category_id = fc.category_id   -- correlation to outer query
)
ORDER BY c.name, f.title;

-- Q7. Customers who have never rented a film
-- Method A: NOT IN
SELECT
    c.customer_id,
    c.first_name,
    c.last_name
FROM customer c
WHERE c.customer_id NOT IN (
    SELECT customer_id FROM rental WHERE customer_id IS NOT NULL
);


-- Note: In the standard dvdrental sample data every customer has rented at
-- least once, so the  queries returns an empty result set here. They are
-- still included because a real-world / partially-seeded database would
-- return rows, and the pattern is the deliverable being demonstrated.

-- Q8. Store with the highest total revenue (subquery in WHERE)
SELECT
    store_id,
    total_revenue
FROM (
    SELECT
        s.store_id,
        SUM(p.amount) AS total_revenue
    FROM payment p
    JOIN staff s ON p.staff_id = s.staff_id
    GROUP BY s.store_id
) AS store_revenue
WHERE total_revenue = (
    SELECT MAX(total_revenue)
    FROM (
        SELECT SUM(p.amount) AS total_revenue
        FROM payment p
        JOIN staff s ON p.staff_id = s.staff_id
        GROUP BY s.store_id
    ) AS store_revenue_2
);

-- PART 3 — CTE & WINDOW FUNCTION CHALLENGES

-- Q9. Rank customers by total spend within each city (CTE + window function)
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.first_name,
        c.last_name,
        ci.city,
        SUM(p.amount) AS total_spent
    FROM customer c
    JOIN address a ON c.address_id = a.address_id
    JOIN city ci ON a.city_id = ci.city_id
    JOIN payment p ON c.customer_id = p.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, ci.city
)
SELECT
    city,
    first_name,
    last_name,
    total_spent,
    RANK() OVER (PARTITION BY city ORDER BY total_spent DESC) AS spend_rank_in_city
FROM customer_spend
ORDER BY city, spend_rank_in_city;

-- Q10. Most recently rented film for each customer (ROW_NUMBER())
WITH ranked_rentals AS (
    SELECT
        r.customer_id,
        f.title,
        r.rental_date,
        ROW_NUMBER() OVER (
            PARTITION BY r.customer_id
            ORDER BY r.rental_date DESC
        ) AS rn
    FROM rental r
    JOIN inventory i ON r.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
)
SELECT
    customer_id,
    title AS most_recent_film,
    rental_date
FROM ranked_rentals
WHERE rn = 1
ORDER BY customer_id;

-- Q11. Month-over-month rental revenue growth (CTE)
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', payment_date) AS revenue_month,
        SUM(amount) AS total_revenue
    FROM payment
    GROUP BY DATE_TRUNC('month', payment_date)
),
revenue_with_growth AS (
    SELECT
        revenue_month,
        total_revenue,
        LAG(total_revenue) OVER (ORDER BY revenue_month) AS prev_month_revenue
    FROM monthly_revenue
)
SELECT
    TO_CHAR(revenue_month, 'YYYY-MM') AS month,
    total_revenue,
    prev_month_revenue,
    CASE
        WHEN prev_month_revenue IS NULL THEN NULL
        ELSE ROUND(
            ((total_revenue - prev_month_revenue) / prev_month_revenue) * 100, 2
        )
    END AS pct_growth_vs_prev_month
FROM revenue_with_growth
ORDER BY revenue_month;

-- Q12. Top 3 highest-grossing films per category (RANK() inside a CTE)
WITH film_revenue AS (
    SELECT
        c.name AS category,
        f.title,
        SUM(p.amount) AS revenue
    FROM payment p
    JOIN rental r ON p.rental_id = r.rental_id
    JOIN inventory i ON r.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
    JOIN film_category fc ON f.film_id = fc.film_id
    JOIN category c ON fc.category_id = c.category_id
    GROUP BY c.name, f.title
),
ranked_films AS (
    SELECT
        category,
        title,
        revenue,
        RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS revenue_rank
    FROM film_revenue
)
SELECT
    category,
    title,
    revenue,
    revenue_rank
FROM ranked_films
WHERE revenue_rank <= 3
ORDER BY category, revenue_rank;

--    BONUS CHALLENGE
--    Which staff member processed the highest revenue in each store,
--    and what percentage of that store's total revenue did they contribute?

WITH staff_revenue AS (
        -- Revenue processed by each staff member, grouped by their store
    SELECT
        s.store_id,
        s.staff_id,
        s.first_name,
        s.last_name,
        SUM(p.amount) AS staff_revenue
    FROM payment p
    JOIN staff s ON p.staff_id = s.staff_id
    GROUP BY s.store_id, s.staff_id, s.first_name, s.last_name
),
store_totals AS (
    -- Total revenue per store (sum across all staff in that store)
    SELECT
        store_id,
        SUM(staff_revenue) AS store_total_revenue
    FROM staff_revenue
    GROUP BY store_id
),
ranked_staff AS (
    -- Rank staff within each store by how much revenue they processed
    SELECT
        sr.store_id,
        sr.staff_id,
        sr.first_name,
        sr.last_name,
        sr.staff_revenue,
        st.store_total_revenue,
        RANK() OVER (PARTITION BY sr.store_id ORDER BY sr.staff_revenue DESC) AS staff_rank
    FROM staff_revenue sr
    JOIN store_totals st ON sr.store_id = st.store_id
)
SELECT
    store_id,
    first_name,
    last_name,
    staff_revenue,
    store_total_revenue,
    ROUND((staff_revenue / store_total_revenue) * 100, 2) AS pct_of_store_revenue
FROM ranked_staff
WHERE staff_rank = 1
ORDER BY store_id;
