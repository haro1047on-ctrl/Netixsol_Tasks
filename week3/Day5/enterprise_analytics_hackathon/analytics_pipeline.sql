SELECT COUNT(*) FROM sales.salesorderheader;
SELECT COUNT(*) FROM sales.customer;
-- =====================================================================
-- STEP 1: Create the analytics schema
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS analytics;


-- =====================================================================
-- STAGE 0: Base Fact Views
-- These are the ONLY views that touch raw sales tables directly.
-- Everything else in this script builds on these two.
-- Expected: sales_line_fact = 121317 rows, sales_order_fact = 31465 rows
-- =====================================================================

CREATE OR REPLACE VIEW analytics.sales_line_fact AS
SELECT
    soh.salesorderid,
    sod.salesorderdetailid,
    soh.orderdate,
    soh.customerid,
    soh.salespersonid,
    soh.territoryid,
    sod.productid,
    sod.orderqty,
    sod.unitprice,
    sod.unitpricediscount,
    ROUND((sod.unitprice * sod.orderqty) * (1 - sod.unitpricediscount), 2) AS line_revenue,
    ROUND(p.standardcost * sod.orderqty, 2)                                 AS line_cost,
    p.productid   AS product_id,
    p.name        AS product_name,
    p.productsubcategoryid
FROM sales.salesorderheader soh
JOIN sales.salesorderdetail sod ON sod.salesorderid = soh.salesorderid
JOIN production.product p       ON p.productid = sod.productid;


CREATE OR REPLACE VIEW analytics.sales_order_fact AS
SELECT
    soh.salesorderid,
    soh.orderdate,
    soh.customerid,
    soh.salespersonid,
    soh.territoryid,
    soh.subtotal,
    soh.taxamt,
    soh.freight,
    soh.totaldue,
    soh.onlineorderflag,
    DATE_TRUNC('month', soh.orderdate)::DATE   AS order_month,
    DATE_TRUNC('quarter', soh.orderdate)::DATE AS order_quarter,
    EXTRACT(YEAR FROM soh.orderdate)::INT      AS order_year
FROM sales.salesorderheader soh;


-- =====================================================================
-- customer_analytics — builds on sales_order_fact
-- Expected: 19119 rows (customers with at least 1 order)
-- =====================================================================
-- =====================================================================
-- analytics.purchasing_fact — the purchasing-domain equivalent of
-- analytics.sales_order_fact
-- =====================================================================

CREATE OR REPLACE VIEW analytics.purchasing_fact AS
SELECT
    poh.purchaseorderid,
    poh.vendorid,
    poh.employeeid,
    poh.orderdate,
    poh.shipdate,
    poh.status,
    poh.subtotal,
    poh.taxamt,
    poh.freight,
    DATE_TRUNC('month', poh.orderdate)::DATE   AS po_month,
    DATE_TRUNC('quarter', poh.orderdate)::DATE AS po_quarter,
    EXTRACT(YEAR FROM poh.orderdate)::INT      AS po_year
FROM purchasing.purchaseorderheader poh;

CREATE OR REPLACE VIEW analytics.customer_analytics AS
WITH snapshot AS (
    -- "As of" date = last order date in the dataset, so recency is
    -- meaningful against the data itself, not today's real-world date
    SELECT MAX(orderdate)::DATE AS snapshot_date FROM analytics.sales_order_fact
),
customer_orders AS (
    SELECT
        sof.customerid,
        COUNT(DISTINCT sof.salesorderid) AS total_orders,
        SUM(sof.subtotal)                AS total_revenue,
        MIN(sof.orderdate)::DATE         AS first_order_date,
        MAX(sof.orderdate)::DATE         AS last_order_date
    FROM analytics.sales_order_fact sof
    GROUP BY sof.customerid
)
SELECT
    c.customerid,
    COALESCE(p.firstname || ' ' || p.lastname, st.name) AS customer_name,
    CASE WHEN c.storeid IS NOT NULL THEN 'Store (B2B)' ELSE 'Individual' END AS customer_type,
    terr.name AS territory,
    co.total_orders,
    ROUND(co.total_revenue, 2) AS total_revenue,
    ROUND(co.total_revenue / NULLIF(co.total_orders, 0), 2) AS avg_order_value,
    co.first_order_date,
    co.last_order_date,
    (s.snapshot_date - co.last_order_date) AS recency_days,
    (co.last_order_date - co.first_order_date) AS tenure_days
FROM sales.customer c
JOIN customer_orders co   ON co.customerid = c.customerid
CROSS JOIN snapshot s
LEFT JOIN person.person p ON p.businessentityid = c.personid
LEFT JOIN sales.store st  ON st.businessentityid = c.storeid
LEFT JOIN sales.salesterritory terr ON terr.territoryid = c.territoryid;


-- =====================================================================
-- customer_segments — builds on customer_analytics (NOT raw tables)
-- Expected: 4 tiers, roughly 4780 customers each
-- =====================================================================

CREATE OR REPLACE VIEW analytics.customer_segments AS
WITH scored AS (
    SELECT
        ca.*,
        NTILE(4) OVER (ORDER BY ca.total_revenue)      AS revenue_score,
        NTILE(4) OVER (ORDER BY ca.total_orders)       AS frequency_score,
        NTILE(4) OVER (ORDER BY ca.recency_days DESC)  AS recency_score  -- more recent = higher score
    FROM analytics.customer_analytics ca
),
rfm AS (
    SELECT
        s.*,
        (s.revenue_score + s.frequency_score + s.recency_score) AS rfm_score
    FROM scored s
)
SELECT
    r.*,
    -- NTILE on the composite score guarantees all 4 tiers are populated,
    -- regardless of how the underlying score distribution clusters
    CASE NTILE(4) OVER (ORDER BY r.rfm_score)
        WHEN 4 THEN 'Platinum'
        WHEN 3 THEN 'Gold'
        WHEN 2 THEN 'Silver'
        ELSE 'Bronze'
    END AS customer_segment
FROM rfm r;


-- =====================================================================
-- product_analytics — builds on sales_line_fact
-- Expected: 504 rows (matches production.product)
-- =====================================================================

CREATE OR REPLACE VIEW analytics.product_analytics AS
SELECT
    p.productid,
    p.name AS product_name,
    pc.name AS category,
    psc.name AS subcategory,
    p.listprice,
    p.standardcost,
    COALESCE(SUM(slf.orderqty), 0)                              AS total_qty_sold,
    COALESCE(ROUND(SUM(slf.line_revenue), 2), 0)                AS total_revenue,
    COALESCE(ROUND(SUM(slf.line_cost), 2), 0)                   AS total_cost,
    COALESCE(ROUND(SUM(slf.line_revenue) - SUM(slf.line_cost), 2), 0) AS total_profit,
    CASE
        WHEN COALESCE(SUM(slf.line_revenue), 0) = 0 THEN NULL
        ELSE ROUND((SUM(slf.line_revenue) - SUM(slf.line_cost)) * 100.0 / SUM(slf.line_revenue), 2)
    END AS profit_margin_pct,
    COUNT(DISTINCT slf.salesorderid) AS orders_containing_product
FROM production.product p
LEFT JOIN production.productsubcategory psc ON psc.productsubcategoryid = p.productsubcategoryid
LEFT JOIN production.productcategory pc     ON pc.productcategoryid = psc.productcategoryid
LEFT JOIN analytics.sales_line_fact slf      ON slf.productid = p.productid
GROUP BY p.productid, p.name, pc.name, psc.name, p.listprice, p.standardcost;


-- =====================================================================
-- inventory_analytics — builds on product_analytics
-- Expected: 504 rows
-- =====================================================================

CREATE OR REPLACE VIEW analytics.inventory_analytics AS
WITH stock_by_product AS (
    SELECT
        pi.productid,
        SUM(pi.quantity) AS total_stock_qty,
        COUNT(DISTINCT pi.locationid) AS num_locations
    FROM production.productinventory pi
    GROUP BY pi.productid
)
SELECT
    pa.productid,
    pa.product_name,
    pa.category,
    pa.subcategory,
    p.safetystocklevel,
    p.reorderpoint,
    COALESCE(sbp.total_stock_qty, 0) AS current_stock_qty,
    COALESCE(sbp.num_locations, 0)   AS num_locations,
    pa.total_qty_sold,
    CASE
        WHEN COALESCE(sbp.total_stock_qty, 0) <= p.reorderpoint THEN 'Reorder Needed'
        WHEN COALESCE(sbp.total_stock_qty, 0) <= p.safetystocklevel THEN 'Low Stock'
        ELSE 'Healthy'
    END AS stock_status,
    ROUND(COALESCE(sbp.total_stock_qty, 0) * p.standardcost, 2) AS inventory_value_at_cost
FROM analytics.product_analytics pa
JOIN production.product p ON p.productid = pa.productid
LEFT JOIN stock_by_product sbp ON sbp.productid = pa.productid;


-- =====================================================================
-- employee_analytics — builds on sales_order_fact
-- Expected: 17 rows (matches sales.salesperson)
-- =====================================================================

CREATE OR REPLACE VIEW analytics.employee_analytics AS
WITH salesperson_orders AS (
    SELECT
        sof.salespersonid,
        COUNT(DISTINCT sof.salesorderid) AS total_orders,
        SUM(sof.subtotal)                AS total_revenue
    FROM analytics.sales_order_fact sof
    WHERE sof.salespersonid IS NOT NULL
    GROUP BY sof.salespersonid
),
latest_quota AS (
    SELECT DISTINCT ON (businessentityid)
        businessentityid, salesquota
    FROM sales.salespersonquotahistory
    ORDER BY businessentityid, quotadate DESC
)
SELECT
    sp.businessentityid AS employee_id,
    p.firstname || ' ' || p.lastname AS employee_name,
    e.jobtitle,
    terr.name AS territory,
    spo.total_orders,
    ROUND(spo.total_revenue, 2) AS total_revenue,
    ROUND(spo.total_revenue / NULLIF(spo.total_orders, 0), 2) AS avg_order_value,
    sp.salesquota AS current_quota,
    lq.salesquota AS latest_quota_history,
    CASE
        WHEN sp.salesquota > 0 THEN ROUND(spo.total_revenue * 100.0 / sp.salesquota, 2)
        ELSE NULL
    END AS pct_of_quota_achieved,
    sp.bonus,
    sp.commissionpct
FROM sales.salesperson sp
JOIN humanresources.employee e ON e.businessentityid = sp.businessentityid
JOIN person.person p           ON p.businessentityid = sp.businessentityid
LEFT JOIN sales.salesterritory terr ON terr.territoryid = sp.territoryid
LEFT JOIN salesperson_orders spo ON spo.salespersonid = sp.businessentityid
LEFT JOIN latest_quota lq ON lq.businessentityid = sp.businessentityid;


-- =====================================================================
-- territory_analytics — builds on sales_order_fact
-- Expected: 10 rows (matches sales.salesterritory)
-- =====================================================================

CREATE OR REPLACE VIEW analytics.territory_analytics AS
WITH territory_yearly AS (
    SELECT
        sof.territoryid,
        sof.order_year,
        SUM(sof.subtotal) AS year_revenue
    FROM analytics.sales_order_fact sof
    WHERE sof.territoryid IS NOT NULL
    GROUP BY sof.territoryid, sof.order_year
),
territory_growth AS (
    -- Year-over-year growth using a window function to compare each year to the prior year
    SELECT
        territoryid,
        order_year,
        year_revenue,
        LAG(year_revenue) OVER (PARTITION BY territoryid ORDER BY order_year) AS prev_year_revenue
    FROM territory_yearly
),
territory_totals AS (
    SELECT
        sof.territoryid,
        COUNT(DISTINCT sof.salesorderid)  AS total_orders,
        COUNT(DISTINCT sof.customerid)    AS unique_customers,
        SUM(sof.subtotal)                 AS total_revenue
    FROM analytics.sales_order_fact sof
    WHERE sof.territoryid IS NOT NULL
    GROUP BY sof.territoryid
),
latest_growth AS (
    SELECT DISTINCT ON (territoryid)
        territoryid,
        order_year AS latest_year,
        year_revenue AS latest_year_revenue,
        prev_year_revenue,
        CASE
            WHEN prev_year_revenue IS NULL OR prev_year_revenue = 0 THEN NULL
            ELSE ROUND((year_revenue - prev_year_revenue) * 100.0 / prev_year_revenue, 2)
        END AS yoy_growth_pct
    FROM territory_growth
    ORDER BY territoryid, order_year DESC
)
SELECT
    t.territoryid,
    t.name AS territory,
    t.group AS region_group,
    t.countryregioncode,
    tt.total_orders,
    tt.unique_customers,
    ROUND(tt.total_revenue, 2) AS total_revenue,
    ROUND(tt.total_revenue / NULLIF(tt.unique_customers, 0), 2) AS avg_revenue_per_customer,
    lg.latest_year,
    ROUND(lg.latest_year_revenue, 2) AS latest_year_revenue,
    lg.yoy_growth_pct,
    RANK() OVER (ORDER BY tt.total_revenue DESC) AS territory_revenue_rank
FROM sales.salesterritory t
JOIN territory_totals tt ON tt.territoryid = t.territoryid
LEFT JOIN latest_growth lg ON lg.territoryid = t.territoryid;

-- NOTE: 2025 is a partial year in this dataset (last order date is
-- 2025-06-29). The "latest_year" row for every territory will show
-- steep negative yoy_growth_pct because it's comparing a half-year
-- to a full year — don't read this as an actual sales collapse.


-- =====================================================================
-- vendor_analytics — builds on raw purchasing tables
-- (this is the purchasing-domain equivalent of sales_order_fact)
-- Expected: 104 rows (matches purchasing.vendor)
-- =====================================================================

CREATE OR REPLACE VIEW analytics.vendor_analytics AS
WITH po_detail_agg AS (
    SELECT
        poh.vendorid,
        poh.purchaseorderid,
        SUM(pod.orderqty)                                    AS total_qty_ordered,
        SUM(pod.receivedqty)                                 AS total_qty_received,
        SUM(pod.rejectedqty)                                 AS total_qty_rejected,
        SUM(pod.orderqty * pod.unitprice)                    AS po_line_total,
        AVG(EXTRACT(DAY FROM (pod.duedate - poh.orderdate))) AS avg_lead_time_days
    FROM purchasing.purchaseorderheader poh
    JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
    GROUP BY poh.vendorid, poh.purchaseorderid
),
vendor_rollup AS (
    SELECT
        vendorid,
        COUNT(DISTINCT purchaseorderid)   AS total_purchase_orders,
        SUM(total_qty_ordered)            AS total_qty_ordered,
        SUM(total_qty_rejected)           AS total_qty_rejected,
        SUM(po_line_total)                AS total_spend,
        ROUND(AVG(avg_lead_time_days), 1) AS avg_lead_time_days
    FROM po_detail_agg
    GROUP BY vendorid
)
SELECT
    v.businessentityid AS vendor_id,
    v.name AS vendor_name,
    v.creditrating,
    v.preferredvendorstatus,
    vr.total_purchase_orders,
    ROUND(vr.total_spend, 2) AS total_spend,
    vr.total_qty_ordered,
    vr.total_qty_rejected,
    CASE
        WHEN vr.total_qty_ordered > 0
        THEN ROUND(vr.total_qty_rejected * 100.0 / vr.total_qty_ordered, 2)
        ELSE NULL
    END AS reject_rate_pct,
    vr.avg_lead_time_days,
    RANK() OVER (ORDER BY vr.total_spend DESC NULLS LAST) AS spend_rank
FROM purchasing.vendor v
LEFT JOIN vendor_rollup vr ON vr.vendorid = v.businessentityid;


-- =====================================================================
-- monthly_revenue — builds on sales_order_fact
-- Feeds Task 3's revenue/growth/trend KPIs directly (37 monthly rows)
-- =====================================================================

CREATE OR REPLACE VIEW analytics.monthly_revenue AS
WITH monthly AS (
    SELECT
        order_month,
        order_year,
        EXTRACT(MONTH FROM order_month)::INT AS month_num,
        COUNT(DISTINCT salesorderid) AS total_orders,
        COUNT(DISTINCT customerid)   AS unique_customers,
        SUM(subtotal)                AS total_revenue
    FROM analytics.sales_order_fact
    GROUP BY order_month, order_year
)
SELECT
    m.*,
    LAG(m.total_revenue) OVER (ORDER BY m.order_month) AS prev_month_revenue,
    ROUND(
        (m.total_revenue - LAG(m.total_revenue) OVER (ORDER BY m.order_month))
        * 100.0 / NULLIF(LAG(m.total_revenue) OVER (ORDER BY m.order_month), 0)
    , 2) AS mom_growth_pct,
    LAG(m.total_revenue, 12) OVER (ORDER BY m.order_month) AS same_month_last_year_revenue,
    ROUND(
        (m.total_revenue - LAG(m.total_revenue, 12) OVER (ORDER BY m.order_month))
        * 100.0 / NULLIF(LAG(m.total_revenue, 12) OVER (ORDER BY m.order_month), 0)
    , 2) AS yoy_growth_pct
FROM monthly m
ORDER BY m.order_month;
--verifying that views were created or not:
SELECT 'sales_order_fact' AS view_name, count(*) FROM analytics.sales_order_fact
UNION ALL SELECT 'sales_line_fact', count(*) FROM analytics.sales_line_fact
UNION ALL SELECT 'customer_analytics', count(*) FROM analytics.customer_analytics
UNION ALL SELECT 'customer_segments', count(*) FROM analytics.customer_segments
UNION ALL SELECT 'product_analytics', count(*) FROM analytics.product_analytics
UNION ALL SELECT 'inventory_analytics', count(*) FROM analytics.inventory_analytics
UNION ALL SELECT 'employee_analytics', count(*) FROM analytics.employee_analytics
UNION ALL SELECT 'territory_analytics', count(*) FROM analytics.territory_analytics
UNION ALL SELECT 'vendor_analytics', count(*) FROM analytics.vendor_analytics
UNION ALL SELECT 'monthly_revenue', count(*) FROM analytics.monthly_revenue;
-------------------------------------------------------------------------------
--Making KPIs
CREATE SCHEMA IF NOT EXISTS kpi;
-------------------------------------------------------------------------------
-- Quarterly Revenue — builds on analytics.sales_order_fact
CREATE OR REPLACE VIEW kpi.quarterly_revenue AS
WITH quarterly AS (
    SELECT
        order_quarter,
        EXTRACT(YEAR FROM order_quarter)::INT AS order_year,
        EXTRACT(QUARTER FROM order_quarter)::INT AS quarter_num,
        COUNT(DISTINCT salesorderid) AS total_orders,
        SUM(subtotal)                AS total_revenue
    FROM analytics.sales_order_fact
    GROUP BY order_quarter
)
SELECT
    q.*,
    LAG(q.total_revenue) OVER (ORDER BY q.order_quarter) AS prev_quarter_revenue,
    ROUND(
        (q.total_revenue - LAG(q.total_revenue) OVER (ORDER BY q.order_quarter))
        * 100.0 / NULLIF(LAG(q.total_revenue) OVER (ORDER BY q.order_quarter), 0)
    , 2) AS qoq_growth_pct
FROM quarterly q
ORDER BY q.order_quarter;

-- Sales Growth Summary — builds on analytics.monthly_revenue (reused, not recalculated)
CREATE OR REPLACE VIEW kpi.sales_growth_summary AS
SELECT
    order_month, order_year, total_orders, total_revenue, mom_growth_pct, yoy_growth_pct,
    CASE
        WHEN mom_growth_pct > 0 THEN 'Growing'
        WHEN mom_growth_pct < 0 THEN 'Declining'
        ELSE 'Flat'
    END AS trend_direction
FROM analytics.monthly_revenue;

-- Best Selling Products — builds on analytics.product_analytics
CREATE OR REPLACE VIEW kpi.best_selling_products AS
SELECT
    productid, product_name, category, subcategory,
    total_qty_sold, total_revenue, profit_margin_pct,
    RANK() OVER (ORDER BY total_qty_sold DESC) AS qty_rank,
    RANK() OVER (ORDER BY total_revenue DESC)  AS revenue_rank
FROM analytics.product_analytics
WHERE total_qty_sold > 0
ORDER BY total_qty_sold DESC
LIMIT 20;

-- Lowest Performing Products — builds on analytics.product_analytics
CREATE OR REPLACE VIEW kpi.lowest_performing_products AS
SELECT
    productid, product_name, category, subcategory,
    total_qty_sold, total_revenue, profit_margin_pct
FROM analytics.product_analytics
ORDER BY total_qty_sold ASC, total_revenue ASC
LIMIT 20;

------------------------------------------------------------------------------
-- Customer Lifetime Value — builds on analytics.customer_segments
CREATE OR REPLACE VIEW kpi.customer_lifetime_value AS
SELECT
    customerid, customer_name, customer_type, territory, customer_segment,
    total_orders, total_revenue AS lifetime_value, avg_order_value, tenure_days,
    ROUND(total_revenue / NULLIF(tenure_days, 0) * 365, 2) AS estimated_annual_value
FROM analytics.customer_segments
ORDER BY total_revenue DESC;

-- Repeat Customers — builds on analytics.customer_analytics
CREATE OR REPLACE VIEW kpi.repeat_customers AS
SELECT
    CASE WHEN total_orders > 1 THEN 'Repeat Customer' ELSE 'One-Time Customer' END AS customer_type_flag,
    COUNT(*) AS num_customers,
    ROUND(AVG(total_orders), 2) AS avg_orders,
    ROUND(AVG(total_revenue), 2) AS avg_revenue,
    ROUND(SUM(total_revenue), 2) AS total_revenue_contribution,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_customers
FROM analytics.customer_analytics
GROUP BY CASE WHEN total_orders > 1 THEN 'Repeat Customer' ELSE 'One-Time Customer' END;

-- Customer Retention (Year over Year) — builds on analytics.sales_order_fact
-- A customer "retained" in year Y if they also ordered in year Y-1
CREATE OR REPLACE VIEW kpi.customer_retention AS
WITH customer_years AS (
    SELECT DISTINCT customerid, order_year
    FROM analytics.sales_order_fact
),
retention_check AS (
    SELECT
        cy.order_year,
        cy.customerid,
        CASE WHEN cy_prev.customerid IS NOT NULL THEN 1 ELSE 0 END AS retained
    FROM customer_years cy
    LEFT JOIN customer_years cy_prev
        ON cy_prev.customerid = cy.customerid
        AND cy_prev.order_year = cy.order_year - 1
)
SELECT
    order_year,
    COUNT(*) AS total_customers_active,
    SUM(retained) AS retained_from_prior_year,
    ROUND(SUM(retained) * 100.0 / COUNT(*), 2) AS retention_rate_pct
FROM retention_check
GROUP BY order_year
ORDER BY order_year;
-------------------------------------------------------------------------------

-- Product Profitability — builds on analytics.product_analytics
CREATE OR REPLACE VIEW kpi.product_profitability AS
SELECT
    productid, product_name, category, subcategory,
    listprice, standardcost, total_qty_sold, total_revenue, total_cost, total_profit, profit_margin_pct,
    CASE
        WHEN profit_margin_pct >= 40 THEN 'High Margin'
        WHEN profit_margin_pct >= 20 THEN 'Medium Margin'
        WHEN profit_margin_pct IS NOT NULL THEN 'Low Margin'
        ELSE 'No Sales'
    END AS margin_tier
FROM analytics.product_analytics
ORDER BY total_profit DESC NULLS LAST;

-- Category Performance — builds on analytics.product_analytics
CREATE OR REPLACE VIEW kpi.category_performance AS
SELECT
    category,
    COUNT(*) AS num_products,
    SUM(total_qty_sold) AS total_qty_sold,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    ROUND(SUM(total_profit), 2) AS total_profit,
    ROUND(SUM(total_profit) * 100.0 / NULLIF(SUM(total_revenue), 0), 2) AS category_margin_pct,
    ROUND(SUM(total_revenue) * 100.0 / SUM(SUM(total_revenue)) OVER (), 2) AS pct_of_total_revenue
FROM analytics.product_analytics
WHERE category IS NOT NULL
GROUP BY category
ORDER BY total_revenue DESC;

-- Product Rankings — builds on analytics.product_analytics
CREATE OR REPLACE VIEW kpi.product_rankings AS
SELECT
    productid, product_name, category, subcategory,
    total_revenue, total_profit, total_qty_sold,
    RANK() OVER (ORDER BY total_revenue DESC)                       AS overall_revenue_rank,
    RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_within_category,
    DENSE_RANK() OVER (ORDER BY profit_margin_pct DESC NULLS LAST)  AS margin_rank
FROM analytics.product_analytics
ORDER BY overall_revenue_rank;
-------------------------------------------------------------------------------


-- Salesperson Rankings — builds on analytics.employee_analytics
CREATE OR REPLACE VIEW kpi.salesperson_rankings AS
SELECT
    employee_id, employee_name, territory, jobtitle,
    total_orders, total_revenue, avg_order_value, pct_of_quota_achieved,
    RANK() OVER (ORDER BY total_revenue DESC)                           AS revenue_rank,
    RANK() OVER (ORDER BY avg_order_value DESC)                         AS avg_order_value_rank,
    RANK() OVER (PARTITION BY territory ORDER BY total_revenue DESC)    AS rank_within_territory
FROM analytics.employee_analytics
WHERE total_revenue IS NOT NULL
ORDER BY revenue_rank;

-- Revenue Contribution by Employee — builds on analytics.employee_analytics
CREATE OR REPLACE VIEW kpi.employee_revenue_contribution AS
SELECT
    employee_id, employee_name, territory, total_revenue,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 2) AS pct_of_total_sales_revenue
FROM analytics.employee_analytics
WHERE total_revenue IS NOT NULL
ORDER BY pct_of_total_sales_revenue DESC;

-- Performance Comparison — builds on analytics.employee_analytics
CREATE OR REPLACE VIEW kpi.employee_performance_comparison AS
SELECT
    employee_id, employee_name, territory,
    total_orders, total_revenue, avg_order_value,
    ROUND(AVG(total_revenue) OVER (), 2) AS company_avg_revenue,
    ROUND(total_revenue - AVG(total_revenue) OVER (), 2) AS revenue_vs_company_avg,
    CASE
        WHEN total_revenue > AVG(total_revenue) OVER () THEN 'Above Average'
        WHEN total_revenue < AVG(total_revenue) OVER () THEN 'Below Average'
        ELSE 'At Average'
    END AS performance_flag
FROM analytics.employee_analytics
WHERE total_revenue IS NOT NULL
ORDER BY total_revenue DESC;
-------------------------------------------------------------------------------


-- Regional Revenue — builds on analytics.territory_analytics
CREATE OR REPLACE VIEW kpi.regional_revenue AS
SELECT
    territory, region_group, countryregioncode,
    total_orders, unique_customers, total_revenue, avg_revenue_per_customer,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 2) AS pct_of_total_revenue
FROM analytics.territory_analytics
ORDER BY total_revenue DESC;

-- Regional Growth — builds on analytics.territory_analytics
CREATE OR REPLACE VIEW kpi.regional_growth AS
SELECT
    territory, region_group, latest_year, latest_year_revenue, yoy_growth_pct,
    CASE
        WHEN yoy_growth_pct > 0 THEN 'Growing'
        WHEN yoy_growth_pct < 0 THEN 'Declining'
        ELSE 'Flat'
    END AS growth_direction
FROM analytics.territory_analytics
ORDER BY yoy_growth_pct DESC NULLS LAST;
-- NOTE: latest_year (2025) is a partial year — every territory will
-- show negative growth here vs. the last FULL year. Not a real collapse.

-- Top Territories — builds on analytics.territory_analytics
CREATE OR REPLACE VIEW kpi.top_territories AS
SELECT territory, region_group, total_revenue, territory_revenue_rank
FROM analytics.territory_analytics
WHERE territory_revenue_rank <= 3
ORDER BY territory_revenue_rank;

-- Lowest Performing Territories — builds on analytics.territory_analytics
CREATE OR REPLACE VIEW kpi.lowest_performing_territories AS
SELECT territory, region_group, total_revenue, territory_revenue_rank
FROM analytics.territory_analytics
ORDER BY territory_revenue_rank DESC
LIMIT 3;
-------------------------------------------------------------------------------


-- Inventory Health — builds on analytics.inventory_analytics
CREATE OR REPLACE VIEW kpi.inventory_health AS
SELECT
    stock_status,
    COUNT(*) AS num_products,
    SUM(current_stock_qty) AS total_units_in_stock,
    ROUND(SUM(inventory_value_at_cost), 2) AS total_inventory_value,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_products
FROM analytics.inventory_analytics
GROUP BY stock_status
ORDER BY CASE stock_status WHEN 'Reorder Needed' THEN 1 WHEN 'Low Stock' THEN 2 ELSE 3 END;

-- Products with Low Stock — builds on analytics.inventory_analytics
CREATE OR REPLACE VIEW kpi.products_low_stock AS
SELECT
    productid, product_name, category, subcategory,
    current_stock_qty, reorderpoint, safetystocklevel, total_qty_sold, stock_status
FROM analytics.inventory_analytics
WHERE stock_status IN ('Reorder Needed', 'Low Stock')
ORDER BY (current_stock_qty - reorderpoint) ASC;

-- Supplier (Vendor) Performance — builds on analytics.vendor_analytics
CREATE OR REPLACE VIEW kpi.supplier_performance AS
SELECT
    vendor_id, vendor_name, creditrating, preferredvendorstatus,
    total_purchase_orders, total_spend, reject_rate_pct, avg_lead_time_days, spend_rank,
    CASE
        WHEN reject_rate_pct <= 2 AND avg_lead_time_days <= 14 THEN 'Reliable'
        WHEN reject_rate_pct > 5 OR avg_lead_time_days > 21 THEN 'At Risk'
        ELSE 'Acceptable'
    END AS supplier_rating
FROM analytics.vendor_analytics
WHERE total_purchase_orders IS NOT NULL
ORDER BY total_spend DESC;

-- Purchasing Trends (Monthly) — builds directly on raw purchasing tables
-- (this is the purchasing-domain equivalent of analytics.monthly_revenue;
-- no purchasing-side monthly view existed yet, so it's created at this stage)
-- Purchasing Trends (Monthly) — builds on analytics.purchasing_fact
CREATE OR REPLACE VIEW kpi.purchasing_trends AS
WITH monthly_po AS (
    SELECT
        po_month,
        COUNT(DISTINCT purchaseorderid) AS total_purchase_orders,
        SUM(subtotal)                   AS total_po_spend
    FROM analytics.purchasing_fact
    GROUP BY po_month
)
SELECT
    po_month, total_purchase_orders, total_po_spend,
    ROUND(
        (total_po_spend - LAG(total_po_spend) OVER (ORDER BY po_month))
        * 100.0 / NULLIF(LAG(total_po_spend) OVER (ORDER BY po_month), 0)
    , 2) AS mom_spend_growth_pct
FROM monthly_po
ORDER BY po_month;
-------------------------------------------------------------------------------
SELECT pg_get_viewdef('kpi.purchasing_trends'::regclass);

--verifying that each query ran accurately or not:
SELECT table_name FROM information_schema.views WHERE table_schema = 'kpi' ORDER BY table_name;

