# Music Store Business Intelligence Pipeline

A chained SQL analysis of the Music Store (Chinook-style) database — customer profiling, segmentation, marketing recommendations, country expansion strategy, and an executive report — built as a single reusable pipeline rather than isolated queries.

**Database:** PostgreSQL, restored from `music_store_postgres.sql`
**Scale:** 59 customers, 412 invoices, 2,240 invoice lines, 3,503 tracks, 24 countries

---

## 1. Segmentation Logic and Justification

Customers are split into **Platinum / Gold / Silver / Bronze** using a **composite score across four factors**, not spend alone:

- Total spend
- Purchase frequency (invoice count)
- Genre diversity (unique genres purchased)
- Artist diversity (unique artists purchased)

**Why not fixed dollar thresholds?** In this dataset almost every customer spends between $36–$50 — a real gap analysis showed spend alone barely separates anyone. A threshold like "spend > $45 = Platinum" would be arbitrary and would ignore genuinely more valuable behaviors like loyalty and variety of taste.

**Method used:** Each of the four factors is scored 1–4 using `NTILE(4)` (quartile-based, 4 = best quartile). The four scores are summed into a `composite_score` (max 16), then bucketed with `CASE WHEN`:

| Composite Score | Segment |
|---|---|
| 14–16 | Platinum |
| 11–13 | Gold |
| 7–10 | Silver |
| ≤6 | Bronze |

This is deliberately **data-driven and relative**, not hardcoded — it stays fair if the store grows or spending patterns shift, and it directly rewards diversity and loyalty, not just wallet size.

**Result on this dataset:** Platinum 10, Gold 19, Silver 17, Bronze 13.

**Notable insight:** Gold generates more *total* revenue (32.67%) than Platinum (17.74%), because Gold has more customers even though Platinum customers spend more individually. This confirms segmentation by multiple factors captures something spend-only ranking would miss — a handful of highly diverse, loyal customers vs. a larger base of solid mid-tier spenders are different business assets.

---

## 2. Country Ranking Methodology

Management wants an expansion target, so six metrics were combined into one **weighted Country Performance Score**, rather than ranking on revenue alone (which would just reward large existing markets and tell management nothing new).

**Metrics used, min-max normalized to a 0–1 scale** (so dollars and counts can be combined fairly):

| Metric | Weight | Rationale |
|---|---|---|
| Total Revenue | 30% | Primary business signal — proven market size |
| Avg Revenue per Customer | 20% | Customer value, independent of market size |
| Avg Invoice Value | 15% | Basket size / spending behavior per transaction |
| Genre Diversity | 15% | Breadth of catalog demand — engagement signal |
| Customer/Artist Diversity | 10% | Depth of musical taste — engagement signal |
| Total Customers | 10% | Market size, weighted lowest since it's the most correlated with revenue already |

**Top 3 recommended for expansion:**

1. **USA** (score 0.7524) — largest existing market by revenue, customers, and diversity. Safest, highest-confidence bet.
2. **Chile** (score 0.4285) — only 1 customer today, but that customer has unusually high spend and genre breadth. This is a **small-sample, high-potential** signal, not a proven market — flagged here explicitly rather than overstated, since one customer isn't statistically reliable on its own.
3. **Canada** (score 0.4238) — the strongest *broad-based* opportunity: 8 customers with consistently good metrics across the board, not dependent on one outlier.

**Recommendation:** Treat USA as "invest further," Canada as "expand with confidence," and Chile as "worth a small pilot campaign to validate before committing budget" — the data supports interest but not certainty for Chile.

---

## 3. Marketing Recommendation Strategy

Each customer's **favorite genre** was found by summing spend per genre per customer and taking the top-ranked genre via `ROW_NUMBER()` (chosen over `RANK()` specifically so ties don't produce two "favorite" genres for the same customer).

Campaigns are then assigned **by segment**, since segment reflects both value and engagement level:

| Segment | Campaign | Reasoning |
|---|---|---|
| Platinum | Early access to new releases | Reward loyalty and diversity with exclusivity — retention play |
| Gold | Album bundle discounts | Encourage bigger baskets from an already-engaged group |
| Silver | Genre-based discount codes | Nudge toward their known favorite genre to increase frequency |
| Bronze | First purchase coupon | Low engagement — focus on getting a second purchase at all |

**Supporting result:** Rock is the top favorite genre in *every* segment on this dataset — a useful but slightly limiting finding. It suggests genre-based campaigns should be secondary personalization (e.g., "your favorite genre is X" messaging) layered on top of the segment-level campaign, rather than the primary lever, since Rock dominance means genre alone won't differentiate segments much here.

---

## 4. Actionable Recommendations

1. **Run a Canada-focused expansion campaign first** — it's the highest-confidence growth market outside the US, backed by 8 real customers rather than a single outlier.
2. **Pilot a small, low-cost campaign in Chile** before committing further budget — validate whether the one high-value customer represents a real market pattern or a one-off.
3. **Protect Gold-tier revenue specifically**, not just Platinum — Gold contributes the largest share of total revenue (32.67%) and is more at risk of churn than Platinum, since Platinum customers are already the most loyal/diverse.
4. **Use Bronze's "first purchase coupon" campaign to measure conversion to Silver**, and track it as a KPI — Bronze is 13 customers who haven't shown loyalty or diversity yet; this segment is the biggest opportunity for lifetime-value growth if it converts.
5. **Layer favorite-genre personalization on top of segment campaigns rather than replacing them** — since Rock dominates every segment, genre alone isn't a strong differentiator here; use it as a secondary personalization touch (e.g. "New Rock releases, early access" for Platinum) rather than the main campaign driver.
6. **Recognize Jane Peacock (top employee, $833.04) and Iron Maiden (top artist, $138.60) as reference points** — worth investigating what's working in Jane's customer relationships and whether more Iron-Maiden-adjacent catalog/marketing could be replicated for similar artists.

---

## 5. Challenges Faced and How They Were Solved

1. **Grain mismatch risk in Task 1.** Joining `invoice` and `invoice_line` directly and aggregating in one pass would double-count `total_spent` and `total_invoices` (each invoice duplicated once per line item). **Solved** by building two separate CTEs at their correct natural grain (invoice-level and invoice-line-level) and joining the pre-aggregated results together, instead of one large nested aggregation.

2. **Segmentation on a narrow spend range.** Spend alone (all customers between $36–$50) wasn't enough to differentiate segments meaningfully. **Solved** by scoring four factors independently with `NTILE(4)` and summing them into a composite score, so segmentation reflects loyalty and diversity, not just a nearly-flat spend distribution.

3. **Combining metrics on different scales for Task 4.** Revenue is in dollars, genre count is a small integer — summing them directly would let revenue dominate the score purely due to units. **Solved** with min-max normalization (`(value - min) / (max - min)`) on every metric before applying weights, so each metric contributes proportionally to its intended weight regardless of its original scale.

4. **`UNION ALL` type mismatches in the bonus pipeline.** Combining 9 differently-shaped reports (counts, dollars, percentages, ranks) into one result set required every branch to return matching column types. **Solved** by defining one generic `label / detail / value_1 / value_2` output shape and explicitly casting values (e.g. `COUNT(*)::NUMERIC`) so every `UNION ALL` branch aligned.

5. **Postgres only allows one `WITH` clause per statement**, which conflicts with wanting 9 separate, cleanly-labeled report outputs for Task 5. **Solved** by using `CREATE TEMP TABLE ... AS` to materialize the Task 1–4 logic once, then writing 9 plain `SELECT`s against those temp tables — genuinely reusing results with zero recalculation, while still producing readable, separately-labeled report grids (better for screenshots than the single-query bonus version).

6. **One-customer countries skewing the expansion ranking.** Chile scored #2 largely on the strength of a single customer. **Solved** not by removing it from the ranking (the data is real), but by explicitly calling out the small-sample caveat in the write-up rather than letting the ranking imply more confidence than the data supports.

---

## 6. Pipeline Structure

```
customer_profile
      ↓
customer_segments
      ↓
customer_favorite_genre → customer_marketing
      ↓
country_metrics
      ↓
country_ranking
      ↓
artist_revenue / album_revenue / employee_revenue
      ↓
Final Executive Dashboard (Task 5 temp-table version, or Bonus single-query version)
```

Each stage is a CTE built directly on the one before it — every later task reuses the previous task's output rather than recalculating it.

---

## 7. Concept Check Answers

**Why are multiple CTEs preferred over one large nested query?**
Multiple CTEs let each stage aggregate at its correct grain before joining, which avoids fan-out bugs (see Challenge #1) and makes each step independently readable and testable, rather than one deeply nested subquery that's hard to debug and easy to get wrong.

**When would you use a window function instead of GROUP BY?**
`GROUP BY` collapses rows into one row per group and loses row-level detail. Window functions (e.g. `RANK() OVER (PARTITION BY ...)`) keep every row while adding calculated context (a rank, a running total, a comparison to the group). Use window functions when you need per-row detail *and* group-level context in the same result — e.g. "this customer's rank within their segment" while still showing the customer's own row.

**Difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()`:**
- `ROW_NUMBER()` — always unique, sequential (1,2,3,4...), even if values tie. Used for "pick exactly one" (Task 3's favorite genre).
- `RANK()` — ties share the same rank, but leaves gaps afterward (1,1,3,4). Used for "official" competitive ranking where ties matter (Task 4's country ranking).
- `DENSE_RANK()` — ties share the same rank, no gaps afterward (1,1,2,3). Useful when you want a compact rank scale without skipped numbers.

**What is conditional aggregation?**
Aggregating (`SUM`, `COUNT`, `AVG`) only over rows that meet a condition, typically using `CASE WHEN` inside the aggregate function — e.g. `SUM(CASE WHEN genre='Rock' THEN spend ELSE 0 END)` to get Rock-only spend without a separate query or `WHERE` clause that would exclude other rows needed elsewhere in the same result.

**How does `CASE WHEN` improve analytical reporting?**
It turns raw numeric or categorical data into business-meaningful labels and buckets directly in SQL (e.g. composite score → "Platinum"/"Gold"/etc.), so reports are immediately readable by non-technical stakeholders without post-processing in another tool.

**Why should SQL queries be broken into logical stages?**
Each stage becomes independently readable, testable, and reusable — a bug or a business-logic change only needs to be fixed in one place, and later stages can be verified against known-correct earlier stages rather than re-deriving everything from scratch every time.

**What makes a SQL query maintainable?**
Descriptive CTE names that describe *what* each stage produces, consistent grain within each CTE, comments marking each pipeline stage, and reuse of prior calculations instead of duplicating logic — so a change in one business rule (e.g. segmentation thresholds) only needs to be updated in one CTE.

---
