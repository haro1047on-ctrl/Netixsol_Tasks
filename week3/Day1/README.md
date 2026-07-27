# SQL Foundations for Data Science — Setup Guide

## Overview
This repository documents the setup and exploration of a PostgreSQL database using the Superstore Sales dataset, as part of SQL Foundations practice for Data Science. It covers installing PostgreSQL and pgAdmin, creating a database and table, importing CSV data, and running basic exploratory SQL queries.

## Dataset
- **Source:** [Superstore Dataset on Kaggle](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final)
- **File:** `Sample - Superstore.csv`
- **Rows / Columns:** 9,994 rows, 21 columns

## Prerequisites
- PostgreSQL (version 15+ recommended)
- pgAdmin 4 (usually bundled with the PostgreSQL installer)
- The Superstore CSV file downloaded locally

## Setup Steps

### 1. Install PostgreSQL
Download PostgreSQL from [postgresql.org/download](https://www.postgresql.org/download/) for your operating system and run the installer. During installation:
- Set a password for the default `postgres` superuser (remember this — you'll need it to connect).
- Keep the default port (`5432`) unless you have a reason to change it.
- The installer typically offers to install pgAdmin alongside PostgreSQL — accept this if prompted.

### 2. Install pgAdmin
If not bundled with your PostgreSQL install, download pgAdmin 4 separately from [pgadmin.org](https://www.pgadmin.org/download/). Launch it and connect to your local PostgreSQL server using the password set in Step 1.

### 3. Create the Database
In pgAdmin:
1. Right-click **Databases** in the left-hand tree → **Create** → **Database**.
2. Name it `superstore_db` (or your preferred name).
3. Click **Save**.

### 4. Create the Table
Open the **Query Tool** on your new database and run a `CREATE TABLE` statement defining the schema, e.g.:

```sql
CREATE TABLE spr_storesales (
    row_id INTEGER PRIMARY KEY,
    order_id VARCHAR(20),
    order_date DATE,
    ship_date DATE,
    ship_mode VARCHAR(20),
    customer_id VARCHAR(20),
    customer_name VARCHAR(100),
    segment VARCHAR(20),
    country VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code INTEGER,
    region VARCHAR(20),
    product_id VARCHAR(20),
    category VARCHAR(30),
    sub_category VARCHAR(30),
    product_name VARCHAR(200),
    sales NUMERIC(10,2),
    quantity INTEGER,
    discount NUMERIC(4,2),
    profit NUMERIC(10,2)
);
```

(See `create_table.sql` in this repo for the exact statement used.)

### 5. Import the CSV
In pgAdmin:
1. Right-click the `spr_storesales` table → **Import/Export Data**.
2. Set direction to **Import**, select the CSV file.
3. Set format to `csv`, delimiter to `,`, and check **Header** so the first row is treated as column names, not data.
4. Click **OK** to run the import.

> **Note:** if the `order_date`/`ship_date` columns fail to import due to date format mismatches (the source CSV uses `M/D/YYYY`), import those two columns as `VARCHAR` instead, then convert them afterward with:
> ```sql
> ALTER TABLE spr_storesales
> ALTER COLUMN order_date TYPE DATE USING to_date(order_date, 'MM/DD/YYYY');
> ```

### 6. Verify the Import
Run the following to confirm the data loaded correctly:

```sql
SELECT COUNT(*) FROM superstore_sales;          -- should return 9994
SELECT * FROM spr_storesales LIMIT 10;
SELECT * FROM information_schema.columns WHERE table_name= 'spr_storesales';
SELECT column_name,data_type FROM information_schema.columns WHERE table_name= 'spr_storesales';

```

## Issues Encountered
- Date columns (`order_date`, `ship_date`) required special handling since PostgreSQL's default `DATE` parsing didn't match the source CSV's `M/D/YYYY` format.
- `information_schema.columns` requires **single quotes** around string values (e.g., `'superstore_sales'`), not double quotes — double quotes are reserved for identifiers in PostgreSQL and will cause a "relation does not exist" error if used for a string comparison.

## Repository Contents
- `concept_check.md` — answers to the SQL concept check questions
- `create_table.sql` — the CREATE TABLE statement used to build the schema
- `screenshots/` — database creation, table import, table structure, and query result screenshots
- `quries.sql` — contains task given quries

### 7. Manually created quries.sql
Kept all used quries except create table query because it was already in create_table.sql