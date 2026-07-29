# DVD Rental Database — Aggregation, Subqueries, CTEs & Window Functions

All queries were written and tested against the restored `dvdrental` database
(15 tables, PostgreSQL). The full, commented SQL is in `aggregation_subqueries.sql`.

---

## Concept Check

**1. What is the difference between WHERE and HAVING?**
`WHERE` filters individual rows *before* grouping happens, it can't reference
an aggregate like `SUM()` or `COUNT()`. `HAVING` filters *groups* after
`GROUP BY` has collapsed rows together, so it's the only place you can write
a condition like `HAVING COUNT(*) > 50`. Rule of thumb: `WHERE` for row-level
filters, `HAVING` for group-level filters.

**2. When would you use a correlated subquery instead of a JOIN?**
When the filtering condition depends on a per-row calculation from the outer
query that would be awkward or impossible to express as a simple join, for example, "the film with the *max* rental rate in *this specific* category"
(Q6). A join would return every film matching some flat condition, but a correlated subquery lets the inner query re-run for each outer row and compare
against a value computed specifically for that row (its category). It's also
useful for existence checks (`EXISTS`/`NOT EXISTS`) where you only care
whether *any* matching row exists, not what its columns are.

**3. What is a CTE, and why is it more readable than a nested subquery?**
A CTE (Common Table Expression), written with `WITH name AS (...)`, is a named,
temporary result set you can reference later in the same query — as if it were
a temporary table. It's more readable than nesting subqueries inside
subqueries because it lets you build a query in linear, top-to-bottom steps
("first calculate this, then calculate that from it") instead of reading
inside-out through several layers of parentheses. CTEs can also be reused
multiple times in the same statement (Q9, Q11, Q12, and the bonus query all
chain 2–3 CTEs together).

**4. Explain the difference between RANK() and DENSE_RANK().**
Both assign a rank number based on `ORDER BY` within each partition. The
difference is how they handle ties: `RANK()` leaves gaps after a tie (e.g.
1, 1, 3, 4 — because two rows tied for 1st, so nobody gets rank 2), while
`DENSE_RANK()` doesn't skip any numbers (1, 1, 2, 3). Use `RANK()` when you
want the gap to reflect "how many rows beat this one"; use `DENSE_RANK()`
when you want a clean, consecutive set of rank labels regardless of ties.

**5. What does PARTITION BY do differently from GROUP BY?**
`GROUP BY` collapses all rows in a group into a single output row — you lose
the individual rows. `PARTITION BY` (used with window functions) keeps every
individual row but lets a function like `RANK()`, `SUM()`, or `ROW_NUMBER()`
"see" only the rows within its partition when doing its calculation. That's
why Q9 can show every customer's own row *and* their rank within their city
in the same result set — something `GROUP BY` alone can't do.

**6. Can a subquery return multiple rows? What operator would you use in that case?**
Yes. A scalar subquery (used with `=`, `>`, `<`, etc.) must return exactly one
row and one column, or Postgres throws an error. If a subquery can return
multiple rows, use `IN`, `NOT IN`, `ANY`, `ALL`, or `EXISTS`/`NOT EXISTS`
instead of a plain comparison operator (see Q7, which uses both `NOT IN` and
`NOT EXISTS` against a multi-row list of customer IDs from the `rental` table).

**7. Give an example of when CASE WHEN is useful inside an aggregate function.**
`CASE WHEN` inside an aggregate lets you build "conditional counts/sums" —
splitting one aggregate into several buckets without separate queries or
self-joins. For example:
```sql
SELECT
    SUM(CASE WHEN amount > 5 THEN 1 ELSE 0 END) AS big_payments,
    SUM(CASE WHEN amount <= 5 THEN 1 ELSE 0 END) AS small_payments
FROM payment;
```
This pattern (sometimes called "pivoting") is exactly how you'd count films
by rating within a single `SUM(CASE WHEN rating = 'PG' THEN 1 END)` per row
instead of running one query per rating.

---

## Subquery vs. CTE vs. Window Function — when to use which

| Tool | Best for | Example in this assignment |
|---|---|---|
| **Subquery (scalar)** | A single value needed for comparison (`WHERE x > (SELECT ...)`) | Q5 (average customer spend), Q8 (max store revenue) |
| **Subquery (correlated)** | A per-row calculation that depends on the outer row | Q6 (max rental rate *per category*) |
| **Subquery (in FROM)** | Treating a query result as a temporary table to filter/aggregate further | Q8 (wrapping store revenue totals) |
| **CTE (`WITH`)** | Multi-step logic that's easier to read top-to-bottom, or reused more than once | Q9, Q11, Q12, Bonus (each chains 2–3 named steps) |
| **Window function** | Calculations that need to compare a row to others in the same group *without* collapsing rows | Q9 (`RANK`), Q10 (`ROW_NUMBER`), Q11 (`LAG`), Q12 (`RANK`) |

In short: reach for a **subquery** when you need one quick, throwaway value;
reach for a **CTE** when the logic has multiple named steps that benefit from
being readable in order; reach for a **window function** whenever the phrase
"top N per group," "rank within," or "compare to the previous row" shows up,
since `GROUP BY` alone can't keep the individual rows around for that.

---

## How each business question was solved

**Part 1 — Aggregation Basics**
- **Q1 (revenue per store):** `payment` doesn't have a `store_id` column
  directly, so it's joined through `staff` (each staff member belongs to one
  store) and summed with `GROUP BY store_id`.
- **Q2 (avg rental duration per category):** Joined `rental → inventory →
  film → film_category → category`, then computed the actual days each film
  was kept (`return_date - rental_date`) and averaged it per category.
  Unreturned rentals (`return_date IS NULL`) are excluded so they don't break
  the date subtraction.
- **Q3 (rentals per month):** `DATE_TRUNC('month', rental_date)` buckets every
  rental into its month, then `COUNT(*)` per bucket.
- **Q4 (categories with >50 films):** Straightforward `GROUP BY` + `HAVING
  COUNT(*) > 50` — the textbook use case for `HAVING`.

**Part 2 — Subquery Challenges**
- **Q5 (above-average spenders):** Inner query sums each customer's payments;
  a second layer averages those per-customer totals to get the true "average
  customer spend" (not the average *payment*, which would be a different and
  much smaller number). Outer query keeps only customers above that average.
- **Q6 (highest rental rate per category, correlated):** For every film row,
  the inner subquery re-computes the max rental rate *for that film's own
  category* (`fc2.category_id = fc.category_id` ties it back to the outer
  row) — a classic correlated subquery.
- **Q7 (customers who never rented):** Solved two ways — `NOT IN` against the
  list of customer IDs that appear in `rental`, and `NOT EXISTS` with a
  correlated check per customer. Both return 0 rows against the standard
  dvdrental dataset (every seeded customer has rented at least once), but the
  patterns are shown because they're the actual deliverable being tested, and
  `NOT EXISTS` is the safer of the two if `customer_id` could ever be `NULL`.
- **Q8 (store with highest revenue):** A subquery in `FROM` builds a small
  per-store revenue table, then a second subquery in `WHERE` finds the single
  maximum value to filter against.

**Part 3 — CTE & Window Function Challenges**
- **Q9 (rank customers by spend within city):** A CTE first computes each
  customer's total spend and city; the outer query then applies
  `RANK() OVER (PARTITION BY city ORDER BY total_spent DESC)` so customers are
  ranked *within their own city* rather than across the whole company.
- **Q10 (most recent rental per customer):** A CTE numbers every rental per
  customer with `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY
  rental_date DESC)`; the outer query keeps only `rn = 1`, i.e. each
  customer's latest rental.
- **Q11 (month-over-month revenue growth):** First CTE sums payments per
  calendar month; second CTE uses `LAG()` to pull in the previous month's
  total next to the current one; the final `SELECT` computes percentage
  growth with a `CASE` to avoid dividing by `NULL` on the very first month.
- **Q12 (top 3 grossing films per category):** First CTE sums revenue per
  film per category (joining `payment → rental → inventory → film →
  film_category → category`); second CTE ranks films within each category
  with `RANK() OVER (PARTITION BY category ORDER BY revenue DESC)`; the final
  filter keeps `revenue_rank <= 3`.
- **Bonus (top staff % of store revenue):** Three chained CTEs — revenue per
  staff member, revenue per store, and a ranking of staff within their store
  — then a final `SELECT` that divides each top staff member's revenue by
  their store's total and multiplies by 100. In the standard dvdrental data
  each store only has one staff member actively processing payments, so both
  stores show 100% — the query is written generally enough to correctly split
  credit if a store ever had multiple active staff.

---

## Three Business Insights

1. **Store revenue is nearly split evenly, but one staff member fully "owns"
   each store's payment processing.** Store 1 processed $30,252.12 and Store
   2 processed $31,059.92 — a roughly 50/50 split. However, the bonus query
   shows each store's revenue was entirely handled by a single staff member
   (100% each), meaning there's no cross-coverage or backup cashier currently
   sharing payment duties. That's a staffing risk worth flagging to
   management — if that one staff member is out, no one else has recent
   payment-processing experience at that location.

2. **A small number of "power renters" drive spend well above the norm.**
   285 of ~599 customers (about 48%) spend more than the company-wide average
   customer total, and the top spender (Eleanor Hunt, $211.55) spends nearly
   double the amount of the customer sitting at the very top of that list's
   tail. This kind of skew suggests a loyalty or rewards program targeted at
   the top 10–15% of spenders (everyone above ~$140) could meaningfully
   protect a large chunk of total revenue, since a relatively small group is
   contributing a disproportionate share.

3. **Rental categories don't just differ by volume — the "long tail" (Sports,
   Games, Comedy) also holds rentals slightly longer on average.** Sports has
   both the most films of any category (74) and the longest average rental
   duration (5.20 days), while Travel has the shortest (4.82 days) despite
   having a similar catalog size. Combined with Q12 showing individual titles
   like *Telegraph Voyage* (Music, $215.75) as clear revenue outliers within
   their category, this suggests category-level marketing and shelf/inventory
   placement decisions should be informed by both *how many* titles a
   category has and *how long* customers tend to keep them — not just raw
   rental counts.

---

