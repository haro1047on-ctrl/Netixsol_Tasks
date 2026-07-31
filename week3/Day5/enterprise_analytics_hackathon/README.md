# Enterprise Analytics Pipeline — AdventureWorks

A reusable analytics layer built on top of the AdventureWorks OLTP database, transforming raw transactional tables into business-ready datasets for executive reporting — without ever re-querying raw tables from the reporting layer.

**Database:** PostgreSQL (AdventureWorks port, 68 tables across 5 schemas: `person`, `humanresources`, `production`, `purchasing`, `sales`)
**Scale:** 31,465 sales orders · 121,317 order lines · 19,820 customers · 504 products · 290 employees · 17 salespeople · 10 territories · 104 vendors · 4,012 purchase orders · 1,069 inventory records
**Date range:** May 30, 2022 – June 29, 2025 (note: 2025 is a partial year)

---

## 1. Database Overview

AdventureWorks models a bicycle manufacturer/retailer selling through two channels:
- **Reseller (offline) orders** — large B2B orders (~$20K average) placed by stores, handled by salespeople
- **Individual (online) orders** — small consumer orders (~$750–$3,200 average), placed directly by customers

The five source schemas map roughly to business domains:

| Schema | Domain |
|---|---|
| `sales` | Orders, customers, salespeople, territories |
| `production` | Products, categories, inventory |
| `purchasing` | Vendors, purchase orders |
| `humanresources` | Employees |
| `person` | Shared identity data (people, addresses) used by both customers and employees |

This structure is normalized for transaction processing, not reporting — getting a simple answer like "revenue by category last quarter" requires joining 4–5 tables every time. The analytics layer exists to do that joining/aggregating once, reusably.

---

## 2. Analytics Architecture

Two schemas were added on top of the raw database:

```
Raw Tables (sales.*, production.*, purchasing.*, humanresources.*, person.*)
      ↓
analytics schema (11 views) — base facts + domain rollups
      ↓
kpi schema (21 views) — dashboard-ready datasets, Task 3 deliverables
      ↓
Python Notebook (pandas + matplotlib) — reads ONLY from analytics.*/kpi.*
```

**Design principle:** every view reads from either raw tables (only at the base "fact" tier) or from other views — never mixing both at the same tier. This is what makes the pipeline a genuine dependency chain rather than a set of isolated queries, and it's what satisfies the Bonus Challenge requirement that a new dashboard only ever needs to read from the analytics layer.

### Dependency chain (abbreviated)

```
sales.salesorderheader/detail ──► analytics.sales_order_fact / sales_line_fact
purchasing.purchaseorderheader ──► analytics.purchasing_fact
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
        analytics.customer_analytics   analytics.product_analytics   analytics.employee_analytics
                    │                     │                     
                    ▼                     ▼                     
        analytics.customer_segments   analytics.inventory_analytics
                    │
      ┌─────────────┴──────────────────────────────────┐
      ▼                                                 ▼
kpi.customer_lifetime_value, repeat_customers,   kpi.best_selling_products, category_performance,
customer_retention                               product_rankings, product_profitability, etc.
```

---

## 3. Intermediate Tables/Views Created

### `analytics` schema (11 views)

| View | Grain | Builds on |
|---|---|---|
| `sales_order_fact` | 1 row / order | raw `sales.salesorderheader` |
| `sales_line_fact` | 1 row / order line | raw `sales.salesorderheader` + `salesorderdetail` + `production.product` |
| `purchasing_fact` | 1 row / purchase order | raw `purchasing.purchaseorderheader` |
| `customer_analytics` | 1 row / customer | `sales_order_fact` |
| `customer_segments` | 1 row / customer | `customer_analytics` |
| `product_analytics` | 1 row / product | `sales_line_fact` |
| `inventory_analytics` | 1 row / product | `product_analytics` |
| `employee_analytics` | 1 row / salesperson | `sales_order_fact` |
| `territory_analytics` | 1 row / territory | `sales_order_fact` |
| `vendor_analytics` | 1 row / vendor | raw `purchasing.*` (purchasing's own base tier) |
| `monthly_revenue` | 1 row / month | `sales_order_fact` |

### `kpi` schema (21 views)

| Domain | Views |
|---|---|
| Sales | `quarterly_revenue`, `sales_growth_summary`, `best_selling_products`, `lowest_performing_products` |
| Customers | `customer_lifetime_value`, `repeat_customers`, `customer_retention` |
| Products | `product_profitability`, `category_performance`, `product_rankings` |
| Employees | `salesperson_rankings`, `employee_revenue_contribution`, `employee_performance_comparison` |
| Territories | `regional_revenue`, `regional_growth`, `top_territories`, `lowest_performing_territories` |
| Inventory/Purchasing | `inventory_health`, `products_low_stock`, `supplier_performance`, `purchasing_trends` |

**32 total views**, well above the assignment's minimum of 10, spanning 6 business domains (exceeding the minimum of 5).

---

## 4. SQL Design Decisions

1. **Two "Stage 0" fact views instead of one.** `sales_order_fact` (order grain) and `sales_line_fact` (order-line grain) are kept separate because collapsing both grains into a single aggregation would double-count order totals once for every line item on that order. Every downstream view picks whichever grain it actually needs, rather than re-deriving both from scratch.

2. **`customer_segments` uses `NTILE()` on a composite score, not fixed thresholds.** An initial design summed three quartile scores (revenue, frequency, recency) and bucketed the sum with fixed cutoffs — but testing showed this produced zero "Bronze" customers, because a customer's revenue, order frequency, and recency tend to move together (nobody scored a 1 on all three). The fix was to apply a second `NTILE(4)` directly on the composite score, guaranteeing all four segments are populated regardless of how the underlying scores cluster.

3. **`customer_analytics` uses dual `LEFT JOIN`s to handle two customer types in one row shape.** A customer is either an individual (linked via `person.person`) or a store/reseller (linked via `sales.store`) — never both. `COALESCE(person_name, store_name)` produces a single clean `customer_name` column regardless of which type the customer is, avoiding the need for two separate customer views.

4. **`purchasing_fact` was added as a dedicated Stage-0 view**, mirroring `sales_order_fact`, specifically so that `kpi.purchasing_trends` would never need to touch a raw table directly. This was a deliberate mid-project fix: the first draft had `purchasing_trends` reading straight from `purchasing.purchaseorderheader`, which technically violated the pipeline's own "views build on views" rule and the Bonus Challenge's requirement that new dashboards only need the analytics layer.

5. **Window functions were chosen over `GROUP BY` wherever row-level detail needed to be kept alongside group-level context** — e.g. `RANK() OVER (PARTITION BY category ...)` in `product_rankings` keeps every product's own row while still showing its rank within its category; a `GROUP BY` approach would have collapsed the products into just their category summary.

6. **Vendor and purchasing metrics were built as a separate lineage from the sales metrics**, rather than folding purchasing into the same fact views as sales — the two domains (selling to customers vs. buying from suppliers) don't share a natural grain, so keeping them as parallel chains (`sales_order_fact` → sales KPIs; `purchasing_fact` → purchasing KPIs) kept each chain simpler than one unified fact table would have been.

---

## 5. Challenges Faced and How They Were Solved

1. **Installing the database itself.** `instawdb.sql` is the SQL Server version and will not run on Postgres; the correct file is `install.sql`, and it requires the CSVs to sit in the same folder and be run via `psql -f install.sql` from a terminal (not pasted into pgAdmin's Query Tool), because the `\copy ... FROM './File.csv'` commands resolve relative paths against the working directory the command is run from.

2. **`customer_segments` initially produced only 3 populated tiers instead of 4** (see Design Decision #2 above) — caught by checking `GROUP BY customer_segment` counts before moving on, not by assuming the CASE WHEN logic was correct just because it ran without errors.

3. **One KPI view initially broke the "views build on views" rule.** `kpi.purchasing_trends` was first built directly against `purchasing.purchaseorderheader` because no purchasing-domain time-series view existed yet at that point in the build. This was caught during a deliberate Step 4 review against the Bonus Challenge requirement, and fixed by adding `analytics.purchasing_fact` and repointing the KPI view at it.

4. **Column naming inconsistency between the raw fact views and the analytics/KPI views** caused a runtime error in the notebook (`analytics.sales_order_fact` uses the raw column name `subtotal`, while every aggregated view above it renames the same concept to `total_revenue`). Solved by explicitly noting which column name applies to which view (documented below in Assumptions) so it doesn't recur.

5. **2025 being a partial year skews every growth calculation that includes it** — `territory_analytics`, `regional_growth`, and `monthly_revenue`/`sales_growth_summary` all show steep negative growth for the most recent period purely because a 6-month year is being compared to a 12-month year. Solved by documenting this explicitly in the affected views and in the executive recommendations, rather than letting the numbers imply an actual sales decline.

6. **Salesperson quota percentages look implausibly high** (1,000%+ in `employee_analytics.pct_of_quota_achieved`) because `salesquota` in the source data is a per-period target while the revenue figure being compared against it is all-time cumulative revenue. Documented as a known limitation rather than "fixed," since correcting it would require deciding which specific quota period to compare against — a business decision, not a SQL bug.

---

## 6. Assumptions Made

1. **"As of" date for recency/tenure calculations** (`customer_analytics.recency_days`, `tenure_days`) is the last order date in the entire dataset (2025-06-29), not the real-world current date — since the dataset is historical, using today's actual date would make every customer look inactive for the wrong reason.

2. **Customer segmentation weights three factors equally** (revenue, order frequency, recency) via three independent `NTILE(4)` scores summed together, rather than a weighted formula — this was a deliberate simplification; a real deployment might weight recency more heavily for a subscription business, or revenue more heavily for a luxury retailer.

3. **"Repeat customer" is defined as having placed more than 1 order, with no time window** — a customer who ordered once in 2022 and once in 2025 counts as "repeat" the same as one who ordered twice in the same month. A stricter definition (e.g., repeat within 12 months) would likely show different, more conservative retention numbers.

4. **Supplier rating thresholds** (`supplier_performance.supplier_rating`: Reliable ≤2% reject rate and ≤14 days lead time; At Risk >5% reject rate or >21 days lead time) were chosen as reasonable illustrative cutoffs, not derived from an industry benchmark — a real procurement team would likely have contractual SLA thresholds to use instead.

5. **Inventory stock status thresholds** (`inventory_analytics.stock_status`) use the product's own `reorderpoint` and `safetystocklevel` columns already present in the source data, rather than a custom formula — trusting that these were set deliberately by whoever originally populated AdventureWorks' product data.

6. **Column naming reference** — since raw-tier and aggregated-tier views use different names for conceptually the same figure:

   | View tier | Column name for revenue |
   |---|---|
   | `analytics.sales_order_fact` (raw-grain fact) | `subtotal` |
   | `analytics.sales_line_fact` (raw-grain fact) | `line_revenue` |
   | Every other `analytics.*` and `kpi.*` view | `total_revenue` |

---

## 7. Executive Recommendations Summary

Full detail with supporting numbers is in the notebook's final section. Headlines:

**Opportunities:** Accessory bundling (50% margin category, underexposed) · retention program for near-repeat customers · Platinum segment pattern-matching · doubling down on the online-channel shift · replicating top-territory playbooks in underperforming regions.

**Risks:** Vendor concentration risk in the largest, imperfect supplier · 19% of catalog needs restocking · retention trending down amid rapid customer growth · one-time buyers may be an unprofitable acquisition channel · 86% revenue concentration in a single category (Bikes).

**Recommendations:** Launch accessory bundling at point-of-sale · build a 2nd/3rd-order retention program · open a vendor quality review with the top supplier · prioritize restocking for products overlapping with Bikes · study and replicate top-territory execution in the bottom 3 regions.

---
# Bonus Challenge Explanation

## Goal
The bonus challenge requires designing the SQL project so that adding a new dashboard in the future requires only reading from analytical tables/views — not from raw transactional tables.

## How this project meets the bonus challenge
The analytics pipeline is intentionally layered:

1. **Raw tables** exist in the source schemas (`sales`, `production`, `purchasing`, `humanresources`, `person`).
2. **Analytics views** are built on raw tables once and exposed in the `analytics` schema.
3. **KPI views** are built only from the `analytics` schema and exposed in the `kpi` schema.
4. **Dashboard and notebook queries** should read only from `analytics.*` or `kpi.*` views.

## Key implementation details
- `analytics.sales_line_fact`, `analytics.sales_order_fact`, and `analytics.purchasing_fact` are the only views that directly query raw tables.
- All downstream views in the `analytics` and `kpi` schemas reuse these base views instead of re-querying the raw sources.
- `kpi.purchasing_trends` is built on `analytics.purchasing_fact`, so purchasing analytics also follow the same reusable pattern.
- The notebook is designed to use `pandas.read_sql()` against final analytical views only, avoiding raw table queries.

## Why this is reusable
A new dashboard can be created by selecting from one or more of these views:
- `kpi.sales_growth_summary`
- `kpi.category_performance`
- `kpi.customer_lifetime_value`
- `kpi.top_territories`
- `kpi.inventory_health`
- `analytics.customer_segments`
- `analytics.product_analytics`

Because these views already encapsulate the data logic, dashboard authors do not need to reimplement joins, aggregates, or business rules.

## Example future workflow
To add a new dashboard chart for "repeat customer revenue share":
- Query `kpi.repeat_customers`
- Use the output directly in the dashboard

No raw table joins or raw table SQL should be needed.

## Conclusion
This project is built as a reusable reporting layer. The analytics layer isolates raw-source complexity, and the KPI layer provides dashboard-ready datasets, which is exactly the structure required by the bonus challenge.