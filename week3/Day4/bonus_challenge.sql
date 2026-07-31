WITH

-- STAGE 1: Customer Profile
customer_invoice_totals AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.country,
        COUNT(DISTINCT i.invoice_id)                      AS total_invoices,
        SUM(i.total)                                       AS total_spent,
        COUNT(DISTINCT TO_CHAR(i.invoice_date, 'YYYY-MM')) AS purchase_months
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
        cit.customer_id, cit.customer_name, cit.country,
        cit.total_spent, cit.total_invoices,
        ROUND(cit.total_spent / cit.total_invoices, 2) AS avg_invoice_value,
        ctd.total_tracks_purchased, ctd.unique_genres, ctd.unique_artists,
        cit.purchase_months
    FROM customer_invoice_totals cit
    JOIN customer_track_details ctd ON ctd.customer_id = cit.customer_id
),

-- STAGE 2: Customer Segments — built directly on customer_profile
customer_scores AS (
    SELECT
        cp.*,
        NTILE(4) OVER (ORDER BY cp.total_spent)    AS spend_score,
        NTILE(4) OVER (ORDER BY cp.total_invoices) AS frequency_score,
        NTILE(4) OVER (ORDER BY cp.unique_genres)  AS genre_score,
        NTILE(4) OVER (ORDER BY cp.unique_artists) AS artist_score
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

-- STAGE 3: Favorite Genres — built on customer_segments
customer_genre_spend AS (
    SELECT c.customer_id, g.name AS genre_name, SUM(il.unit_price * il.quantity) AS genre_spend
    FROM customer c
    JOIN invoice i       ON i.customer_id = c.customer_id
    JOIN invoice_line il ON il.invoice_id = i.invoice_id
    JOIN track t         ON t.track_id = il.track_id
    JOIN genre g         ON g.genre_id = t.genre_id
    GROUP BY c.customer_id, g.name
),

customer_favorite_genre AS (
    SELECT customer_id, genre_name AS favorite_genre
    FROM (
        SELECT cgs.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY genre_spend DESC) AS rn
        FROM customer_genre_spend cgs
    ) x
    WHERE rn = 1
),

customer_marketing AS (
    SELECT
        cs.customer_id, cs.customer_segment, cs.total_spent, cfg.favorite_genre,
        CASE cs.customer_segment
            WHEN 'Platinum' THEN 'Early access to new releases'
            WHEN 'Gold'     THEN 'Album bundle discounts'
            WHEN 'Silver'   THEN 'Genre-based discount codes'
            WHEN 'Bronze'   THEN 'First purchase coupon'
        END AS recommended_campaign
    FROM customer_segments cs
    JOIN customer_favorite_genre cfg ON cfg.customer_id = cs.customer_id
),

-- STAGE 4: Country Metrics
country_base_metrics AS (
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

-- STAGE 5: Country Ranking — built directly on country_metrics
country_normalized AS (
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
    SELECT
        cs.*,
        RANK() OVER (ORDER BY cs.country_score DESC)               AS expansion_rank,
        RANK() OVER (ORDER BY cs.total_revenue DESC)                AS revenue_rank,
        ROUND(cs.total_revenue * 100.0 / SUM(cs.total_revenue) OVER (), 2) AS revenue_contribution_pct
    FROM country_scores cs
),

-- STAGE 6: Artist / Album / Employee Revenue — new dimensions for the dashboard
artist_revenue AS (
    SELECT
        ar.name AS artist_name,
        SUM(il.unit_price * il.quantity) AS total_revenue,
        RANK() OVER (ORDER BY SUM(il.unit_price * il.quantity) DESC) AS revenue_rank
    FROM artist ar
    JOIN album al        ON al.artist_id = ar.artist_id
    JOIN track t          ON t.album_id = al.album_id
    JOIN invoice_line il  ON il.track_id = t.track_id
    GROUP BY ar.artist_id, ar.name
),

album_revenue AS (
    SELECT
        al.title AS album_title, ar.name AS artist_name,
        SUM(il.unit_price * il.quantity) AS total_revenue,
        RANK() OVER (ORDER BY SUM(il.unit_price * il.quantity) DESC) AS revenue_rank
    FROM album al
    JOIN artist ar        ON ar.artist_id = al.artist_id
    JOIN track t          ON t.album_id = al.album_id
    JOIN invoice_line il  ON il.track_id = t.track_id
    GROUP BY al.album_id, al.title, ar.name
),

employee_revenue AS (
    SELECT
        e.first_name || ' ' || e.last_name AS employee_name,
        SUM(i.total) AS total_revenue,
        RANK() OVER (ORDER BY SUM(i.total) DESC) AS revenue_rank
    FROM employee e
    JOIN customer c ON c.support_rep_id = e.employee_id
    JOIN invoice i  ON i.customer_id = c.customer_id
    GROUP BY e.employee_id, e.first_name, e.last_name
),

-- STAGE 7: Segment-level rollups used by the final dashboard
segment_top_customer AS (
    SELECT customer_segment, customer_name, total_spent
    FROM (
        SELECT customer_segment, customer_name, total_spent,
               ROW_NUMBER() OVER (PARTITION BY customer_segment ORDER BY total_spent DESC) AS rn
        FROM customer_segments
    ) x
    WHERE rn = 1
),

segment_top_genre AS (
    SELECT customer_segment, favorite_genre
    FROM (
        SELECT cs.customer_segment, cfg.favorite_genre,
               ROW_NUMBER() OVER (PARTITION BY cs.customer_segment ORDER BY COUNT(*) DESC) AS rn
        FROM customer_segments cs
        JOIN customer_favorite_genre cfg ON cfg.customer_id = cs.customer_id
        GROUP BY cs.customer_segment, cfg.favorite_genre
    ) x
    WHERE rn = 1
)

-- =====================================================================
-- FINAL STAGE: Executive Dashboard — one unified result set
-- =====================================================================
SELECT 1 AS section_order, 'Customer Segment Summary' AS report_section,
       customer_segment AS label, NULL AS detail,
       COUNT(*)::NUMERIC AS value_1, ROUND(AVG(total_spent),2) AS value_2
FROM customer_segments
GROUP BY customer_segment

UNION ALL
SELECT 2, 'Revenue by Segment', customer_segment, NULL,
       ROUND(SUM(total_spent),2),
       ROUND(SUM(total_spent) * 100.0 / SUM(SUM(total_spent)) OVER (), 2)
FROM customer_segments
GROUP BY customer_segment

UNION ALL
SELECT 3, 'Top Customer per Segment', customer_segment, customer_name, total_spent, NULL
FROM segment_top_customer

UNION ALL
SELECT 4, 'Top Genre per Segment', customer_segment, favorite_genre, NULL, NULL
FROM segment_top_genre

UNION ALL
SELECT 5, 'Best Performing Country', country, NULL, total_revenue, revenue_contribution_pct
FROM country_ranking
WHERE revenue_rank = 1

UNION ALL
SELECT 6, 'Revenue Contribution by Country (Top 5)', country, NULL, total_revenue, revenue_contribution_pct
FROM country_ranking
WHERE revenue_rank <= 5

UNION ALL
SELECT 7, 'Top 3 Countries for Expansion', country, NULL, country_score, expansion_rank
FROM country_ranking
WHERE expansion_rank <= 3

UNION ALL
SELECT 8, 'Top Employee by Revenue', employee_name, NULL, total_revenue, NULL
FROM employee_revenue
WHERE revenue_rank = 1

UNION ALL
SELECT 9, 'Top Artist by Revenue', artist_name, NULL, total_revenue, NULL
FROM artist_revenue
WHERE revenue_rank = 1

UNION ALL
SELECT 10, 'Top Album by Revenue', album_title, artist_name, total_revenue, NULL
FROM album_revenue
WHERE revenue_rank = 1

ORDER BY section_order, value_1 DESC NULLS LAST;