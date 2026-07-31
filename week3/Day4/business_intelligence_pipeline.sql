--Task 1 — Customer Spending Profile
WITH customer_invoice_totals AS (
    -- One row per customer, aggregated at the invoice level
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.country,
        COUNT(DISTINCT i.invoice_id)                              AS total_invoices,
        SUM(i.total)                                               AS total_spent,
        COUNT(DISTINCT TO_CHAR(i.invoice_date, 'YYYY-MM'))         AS purchase_months
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, c.country
),

customer_track_details AS (
    -- One row per customer, aggregated at the track/genre/artist level
    SELECT
        c.customer_id,
        SUM(il.quantity)                    AS total_tracks_purchased,
        COUNT(DISTINCT t.genre_id)          AS unique_genres,
        COUNT(DISTINCT al.artist_id)        AS unique_artists
    FROM customer c
    JOIN invoice i        ON i.customer_id = c.customer_id
    JOIN invoice_line il  ON il.invoice_id = i.invoice_id
    JOIN track t          ON t.track_id = il.track_id
    LEFT JOIN album al    ON al.album_id = t.album_id
    GROUP BY c.customer_id
)

SELECT
    cit.customer_id,
    cit.customer_name,
    cit.country,
    cit.total_spent,
    cit.total_invoices,
    ROUND(cit.total_spent / cit.total_invoices, 2)  AS avg_invoice_value,
    ctd.total_tracks_purchased,
    ctd.unique_genres,
    ctd.unique_artists,
    cit.purchase_months
FROM customer_invoice_totals cit
JOIN customer_track_details ctd ON ctd.customer_id = cit.customer_id
ORDER BY cit.total_spent DESC;

--Task 2 — Customer Segmentation
WITH customer_invoice_totals AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.country,
        COUNT(DISTINCT i.invoice_id)                        AS total_invoices,
        SUM(i.total)                                         AS total_spent,
        COUNT(DISTINCT TO_CHAR(i.invoice_date, 'YYYY-MM'))   AS purchase_months
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, c.country
),

customer_track_details AS (
    SELECT
        c.customer_id,
        SUM(il.quantity)              AS total_tracks_purchased,
        COUNT(DISTINCT t.genre_id)    AS unique_genres,
        COUNT(DISTINCT al.artist_id)  AS unique_artists
    FROM customer c
    JOIN invoice i        ON i.customer_id = c.customer_id
    JOIN invoice_line il  ON il.invoice_id = i.invoice_id
    JOIN track t          ON t.track_id = il.track_id
    LEFT JOIN album al    ON al.album_id = t.album_id
    GROUP BY c.customer_id
),

customer_profile AS (
    -- This IS Task 1's output — reused, not rebuilt
    SELECT
        cit.customer_id,
        cit.customer_name,
        cit.country,
        cit.total_spent,
        cit.total_invoices,
        ROUND(cit.total_spent / cit.total_invoices, 2) AS avg_invoice_value,
        ctd.total_tracks_purchased,
        ctd.unique_genres,
        ctd.unique_artists,
        cit.purchase_months
    FROM customer_invoice_totals cit
    JOIN customer_track_details ctd ON ctd.customer_id = cit.customer_id
),

customer_scores AS (
    -- Score each factor 1-4 by quartile (4 = best) using NTILE,
    -- instead of hardcoded dollar cutoffs — keeps it fair even as data grows
    SELECT
        cp.*,
        NTILE(4) OVER (ORDER BY cp.total_spent)        AS spend_score,
        NTILE(4) OVER (ORDER BY cp.total_invoices)     AS frequency_score,
        NTILE(4) OVER (ORDER BY cp.unique_genres)      AS genre_score,
        NTILE(4) OVER (ORDER BY cp.unique_artists)     AS artist_score
    FROM customer_profile cp
),

customer_segments AS (
    SELECT
        cs.*,
        (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) AS composite_score,
        CASE
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 14 THEN 'Platinum'
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 11 THEN 'Gold'
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 7  THEN 'Silver'
            ELSE 'Bronze'
        END AS customer_segment
    FROM customer_scores cs
)

SELECT
    customer_id, customer_name, country, total_spent, total_invoices,
    avg_invoice_value, unique_genres, unique_artists, composite_score, customer_segment
FROM customer_segments
ORDER BY composite_score DESC, total_spent DESC;

--Task 3 — Personalized Marketing Recommendation
-- (same customer_invoice_totals / customer_track_details / customer_profile /
--  customer_scores / customer_segments CTEs as Task 2 — reused, not repeated below for brevity,
--  include them at the top of your script)

WITH customer_invoice_totals AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.country,
        COUNT(DISTINCT i.invoice_id)                        AS total_invoices,
        SUM(i.total)                                         AS total_spent,
        COUNT(DISTINCT TO_CHAR(i.invoice_date, 'YYYY-MM'))   AS purchase_months
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, c.country
),

customer_track_details AS (
    SELECT
        c.customer_id,
        SUM(il.quantity)              AS total_tracks_purchased,
        COUNT(DISTINCT t.genre_id)    AS unique_genres,
        COUNT(DISTINCT al.artist_id)  AS unique_artists
    FROM customer c
    JOIN invoice i        ON i.customer_id = c.customer_id
    JOIN invoice_line il  ON il.invoice_id = i.invoice_id
    JOIN track t          ON t.track_id = il.track_id
    LEFT JOIN album al    ON al.album_id = t.album_id
    GROUP BY c.customer_id
),

customer_profile AS (
    SELECT
        cit.customer_id,
        cit.customer_name,
        cit.country,
        cit.total_spent,
        cit.total_invoices,
        ROUND(cit.total_spent / cit.total_invoices, 2) AS avg_invoice_value,
        ctd.total_tracks_purchased,
        ctd.unique_genres,
        ctd.unique_artists,
        cit.purchase_months
    FROM customer_invoice_totals cit
    JOIN customer_track_details ctd ON ctd.customer_id = cit.customer_id
),

customer_scores AS (
    SELECT
        cp.*,
        NTILE(4) OVER (ORDER BY cp.total_spent)     AS spend_score,
        NTILE(4) OVER (ORDER BY cp.total_invoices)  AS frequency_score,
        NTILE(4) OVER (ORDER BY cp.unique_genres)   AS genre_score,
        NTILE(4) OVER (ORDER BY cp.unique_artists)  AS artist_score
    FROM customer_profile cp
),

customer_segments AS (
    SELECT
        cs.*,
        (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) AS composite_score,
        CASE
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 14 THEN 'Platinum'
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 11 THEN 'Gold'
            WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 7  THEN 'Silver'
            ELSE 'Bronze'
        END AS customer_segment
    FROM customer_scores cs
),

customer_genre_spend AS (
    SELECT
        c.customer_id,
        g.name                                  AS genre_name,
        SUM(il.unit_price * il.quantity)        AS genre_spend
    FROM customer c
    JOIN invoice i       ON i.customer_id = c.customer_id
    JOIN invoice_line il ON il.invoice_id = i.invoice_id
    JOIN track t         ON t.track_id = il.track_id
    JOIN genre g          ON g.genre_id = t.genre_id
    GROUP BY c.customer_id, g.name
),

ranked_customer_genres AS (
    SELECT
        cgs.*,
        ROW_NUMBER() OVER (PARTITION BY cgs.customer_id ORDER BY cgs.genre_spend DESC) AS genre_rank
    FROM customer_genre_spend cgs
),

customer_favorite_genre AS (
    SELECT customer_id, genre_name AS favorite_genre
    FROM ranked_customer_genres
    WHERE genre_rank = 1
),

customer_marketing AS (
    SELECT
        cs.customer_id,
        cs.customer_name,
        cs.country,
        cs.customer_segment,
        cs.total_spent,
        cfg.favorite_genre,
        CASE cs.customer_segment
            WHEN 'Platinum' THEN 'Early access to new releases'
            WHEN 'Gold'     THEN 'Album bundle discounts'
            WHEN 'Silver'   THEN 'Genre-based discount codes'
            WHEN 'Bronze'   THEN 'First purchase coupon'
        END AS recommended_campaign
    FROM customer_segments cs
    JOIN customer_favorite_genre cfg ON cfg.customer_id = cs.customer_id
)

SELECT *
FROM customer_marketing
ORDER BY customer_segment, total_spent DESC;

--Task 4 — Country Expansion Strategy
WITH country_base_metrics AS (
    SELECT
        c.country,
        COUNT(DISTINCT c.customer_id)                           AS total_customers,
        COUNT(DISTINCT i.invoice_id)                            AS total_invoices,
        SUM(i.total)                                            AS total_revenue,
        ROUND(SUM(i.total) / COUNT(DISTINCT c.customer_id), 2)  AS avg_revenue_per_customer,
        ROUND(SUM(i.total) / COUNT(DISTINCT i.invoice_id), 2)   AS avg_invoice_value
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.country
),

country_diversity_metrics AS (
    SELECT
        c.country,
        COUNT(DISTINCT t.genre_id)   AS genres_purchased,
        COUNT(DISTINCT al.artist_id) AS customer_diversity
    FROM customer c
    JOIN invoice i        ON i.customer_id = c.customer_id
    JOIN invoice_line il  ON il.invoice_id = i.invoice_id
    JOIN track t          ON t.track_id = il.track_id
    LEFT JOIN album al    ON al.album_id = t.album_id
    GROUP BY c.country
),

country_metrics AS (
    SELECT cbm.*, cdm.genres_purchased, cdm.customer_diversity
    FROM country_base_metrics cbm
    JOIN country_diversity_metrics cdm ON cdm.country = cbm.country
),

country_normalized AS (
    -- Min-max normalize each metric to 0-1 so dollars and counts can be combined fairly
    SELECT
        cm.*,
        (cm.total_revenue - MIN(cm.total_revenue) OVER ())::NUMERIC
            / NULLIF(MAX(cm.total_revenue) OVER () - MIN(cm.total_revenue) OVER (), 0) AS revenue_norm,
        (cm.avg_revenue_per_customer - MIN(cm.avg_revenue_per_customer) OVER ())::NUMERIC
            / NULLIF(MAX(cm.avg_revenue_per_customer) OVER () - MIN(cm.avg_revenue_per_customer) OVER (), 0) AS arpc_norm,
        (cm.avg_invoice_value - MIN(cm.avg_invoice_value) OVER ())::NUMERIC
            / NULLIF(MAX(cm.avg_invoice_value) OVER () - MIN(cm.avg_invoice_value) OVER (), 0) AS aiv_norm,
        (cm.genres_purchased - MIN(cm.genres_purchased) OVER ())::NUMERIC
            / NULLIF(MAX(cm.genres_purchased) OVER () - MIN(cm.genres_purchased) OVER (), 0) AS genre_norm,
        (cm.customer_diversity - MIN(cm.customer_diversity) OVER ())::NUMERIC
            / NULLIF(MAX(cm.customer_diversity) OVER () - MIN(cm.customer_diversity) OVER (), 0) AS diversity_norm,
        (cm.total_customers - MIN(cm.total_customers) OVER ())::NUMERIC
            / NULLIF(MAX(cm.total_customers) OVER () - MIN(cm.total_customers) OVER (), 0) AS customers_norm
    FROM country_metrics cm
),

country_scores AS (
    -- Weights: Revenue 30%, Avg Revenue/Customer 20%, Avg Invoice Value 15%,
    --          Genre Diversity 15%, Artist Diversity 10%, Total Customers 10%
    SELECT
        cn.*,
        ROUND(
            (COALESCE(cn.revenue_norm, 0)   * 0.30) +
            (COALESCE(cn.arpc_norm, 0)      * 0.20) +
            (COALESCE(cn.aiv_norm, 0)       * 0.15) +
            (COALESCE(cn.genre_norm, 0)     * 0.15) +
            (COALESCE(cn.diversity_norm, 0) * 0.10) +
            (COALESCE(cn.customers_norm, 0) * 0.10)
        , 4) AS country_score
    FROM country_normalized cn
),

country_ranking AS (
    SELECT cs.*, RANK() OVER (ORDER BY cs.country_score DESC) AS expansion_rank
    FROM country_scores cs
)

SELECT expansion_rank, country, total_customers, total_revenue,
       avg_revenue_per_customer, avg_invoice_value, genres_purchased,
       customer_diversity, country_score
FROM country_ranking
ORDER BY expansion_rank;

--Task 5 — Executive SQL Report
-- Stage 1: build reusable temp tables (calculated once)
DROP TABLE IF EXISTS tmp_customer_segments;
DROP TABLE IF EXISTS tmp_customer_favorite_genre;
DROP TABLE IF EXISTS tmp_country_ranking;
DROP TABLE IF EXISTS tmp_employee_revenue;
DROP TABLE IF EXISTS tmp_artist_revenue;
DROP TABLE IF EXISTS tmp_album_revenue;

CREATE TEMP TABLE tmp_customer_segments AS
WITH customer_invoice_totals AS (
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer_name, c.country,
           COUNT(DISTINCT i.invoice_id) AS total_invoices, SUM(i.total) AS total_spent
    FROM customer c JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name, c.country
),
customer_track_details AS (
    SELECT c.customer_id, COUNT(DISTINCT t.genre_id) AS unique_genres, COUNT(DISTINCT al.artist_id) AS unique_artists
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    JOIN invoice_line il ON il.invoice_id = i.invoice_id
    JOIN track t ON t.track_id = il.track_id
    LEFT JOIN album al ON al.album_id = t.album_id
    GROUP BY c.customer_id
),
customer_profile AS (
    SELECT cit.customer_id, cit.customer_name, cit.country, cit.total_spent, cit.total_invoices,
           ROUND(cit.total_spent / cit.total_invoices, 2) AS avg_invoice_value,
           ctd.unique_genres, ctd.unique_artists
    FROM customer_invoice_totals cit JOIN customer_track_details ctd ON ctd.customer_id = cit.customer_id
),
customer_scores AS (
    SELECT cp.*,
           NTILE(4) OVER (ORDER BY cp.total_spent)    AS spend_score,
           NTILE(4) OVER (ORDER BY cp.total_invoices) AS frequency_score,
           NTILE(4) OVER (ORDER BY cp.unique_genres)  AS genre_score,
           NTILE(4) OVER (ORDER BY cp.unique_artists) AS artist_score
    FROM customer_profile cp
)
SELECT cs.*,
       (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) AS composite_score,
       CASE
           WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 14 THEN 'Platinum'
           WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 11 THEN 'Gold'
           WHEN (cs.spend_score + cs.frequency_score + cs.genre_score + cs.artist_score) >= 7  THEN 'Silver'
           ELSE 'Bronze'
       END AS customer_segment
FROM customer_scores cs;

CREATE TEMP TABLE tmp_customer_favorite_genre AS
WITH customer_genre_spend AS (
    SELECT c.customer_id, g.name AS genre_name, SUM(il.unit_price * il.quantity) AS genre_spend
    FROM customer c
    JOIN invoice i ON i.customer_id = c.customer_id
    JOIN invoice_line il ON il.invoice_id = i.invoice_id
    JOIN track t ON t.track_id = il.track_id
    JOIN genre g ON g.genre_id = t.genre_id
    GROUP BY c.customer_id, g.name
)
SELECT customer_id, genre_name AS favorite_genre
FROM (
    SELECT cgs.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY genre_spend DESC) AS rn
    FROM customer_genre_spend cgs
) x WHERE rn = 1;

CREATE TEMP TABLE tmp_country_ranking AS
WITH country_metrics AS (
    SELECT c.country, COUNT(DISTINCT c.customer_id) AS total_customers, SUM(i.total) AS total_revenue
    FROM customer c JOIN invoice i ON i.customer_id = c.customer_id
    GROUP BY c.country
)
SELECT cm.*,
       RANK() OVER (ORDER BY cm.total_revenue DESC) AS revenue_rank,
       ROUND(cm.total_revenue * 100.0 / SUM(cm.total_revenue) OVER (), 2) AS revenue_contribution_pct
FROM country_metrics cm;

CREATE TEMP TABLE tmp_employee_revenue AS
SELECT e.employee_id, e.first_name || ' ' || e.last_name AS employee_name,
       SUM(i.total) AS total_revenue,
       RANK() OVER (ORDER BY SUM(i.total) DESC) AS revenue_rank
FROM employee e
JOIN customer c ON c.support_rep_id = e.employee_id
JOIN invoice i  ON i.customer_id = c.customer_id
GROUP BY e.employee_id, e.first_name, e.last_name;

CREATE TEMP TABLE tmp_artist_revenue AS
SELECT ar.artist_id, ar.name AS artist_name,
       SUM(il.unit_price * il.quantity) AS total_revenue,
       RANK() OVER (ORDER BY SUM(il.unit_price * il.quantity) DESC) AS revenue_rank
FROM artist ar
JOIN album al ON al.artist_id = ar.artist_id
JOIN track t ON t.album_id = al.album_id
JOIN invoice_line il ON il.track_id = t.track_id
GROUP BY ar.artist_id, ar.name;

CREATE TEMP TABLE tmp_album_revenue AS
SELECT al.album_id, al.title AS album_title, ar.name AS artist_name,
       SUM(il.unit_price * il.quantity) AS total_revenue,
       RANK() OVER (ORDER BY SUM(il.unit_price * il.quantity) DESC) AS revenue_rank
FROM album al
JOIN artist ar ON ar.artist_id = al.artist_id
JOIN track t ON t.album_id = al.album_id
JOIN invoice_line il ON il.track_id = t.track_id
GROUP BY al.album_id, al.title, ar.name;

-- REPORT 1: Customer Segment Summary
SELECT customer_segment, COUNT(*) AS num_customers, ROUND(AVG(total_spent), 2) AS avg_spent_per_customer
FROM tmp_customer_segments GROUP BY customer_segment ORDER BY avg_spent_per_customer DESC;

-- REPORT 2: Revenue by Segment
SELECT customer_segment, ROUND(SUM(total_spent), 2) AS segment_revenue,
       ROUND(SUM(total_spent) * 100.0 / SUM(SUM(total_spent)) OVER (), 2) AS pct_of_total_revenue
FROM tmp_customer_segments GROUP BY customer_segment ORDER BY segment_revenue DESC;

-- REPORT 3: Top Customer in Each Segment
SELECT customer_segment, customer_name, total_spent FROM (
    SELECT customer_segment, customer_name, total_spent,
           ROW_NUMBER() OVER (PARTITION BY customer_segment ORDER BY total_spent DESC) AS rn
    FROM tmp_customer_segments
) x WHERE rn = 1 ORDER BY total_spent DESC;

-- REPORT 4: Top Genre in Each Segment
SELECT customer_segment, favorite_genre, customers_who_prefer_it FROM (
    SELECT cs.customer_segment, cfg.favorite_genre, COUNT(*) AS customers_who_prefer_it,
           ROW_NUMBER() OVER (PARTITION BY cs.customer_segment ORDER BY COUNT(*) DESC) AS rn
    FROM tmp_customer_segments cs
    JOIN tmp_customer_favorite_genre cfg ON cfg.customer_id = cs.customer_id
    GROUP BY cs.customer_segment, cfg.favorite_genre
) x WHERE rn = 1;

-- REPORT 5: Best Performing Country
SELECT country, total_customers, total_revenue, revenue_contribution_pct
FROM tmp_country_ranking WHERE revenue_rank = 1;

-- REPORT 6: Revenue Contribution by Country (Top 10)
SELECT country, total_revenue, revenue_contribution_pct, revenue_rank
FROM tmp_country_ranking ORDER BY revenue_rank LIMIT 10;

-- REPORT 7: Top Employee by Revenue
SELECT employee_name, total_revenue FROM tmp_employee_revenue WHERE revenue_rank = 1;

-- REPORT 8: Top Artist by Revenue
SELECT artist_name, total_revenue FROM tmp_artist_revenue WHERE revenue_rank = 1;

-- REPORT 9: Top Album by Revenue
SELECT album_title, artist_name, total_revenue FROM tmp_album_revenue WHERE revenue_rank = 1;

