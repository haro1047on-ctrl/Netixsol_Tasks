# SQL Foundations for Data Science — Concept Check

## 1. What problem does SQL solve that CSV files cannot?
First problem that i analyzed was that everytime i saved dataframe as csv it loses datatypes, it gets slow when we pass through a few hundered thousand rows, csv is a plain text and their are no relationships between files, just one dataframe with a lot of data in form of plain text not even maintaining the datatypes.
But SQL files solve these problems, these enforce structure via schemas (defined column types, constraints), supports relationships between multiple tables (this is the big conceptual leap from Pandas, instead of one big merged DataFrame, you keep data in smaller, connected tables and combine them on demand via queries), and is built to handle millions or billions of rows efficiently without loading everything into the  memory all at once. 

## 2. What is the difference between a database table and a spreadsheet?
A spreadsheet is for entering data and making calculations manually, as the data increases gradually the spreadsheet gets slower gradually as well adds some structure (formulas, formatting) but still fundamentally single-file, not built for huge datasets, and prone to manual-editing errors.
A database table is like a DataFrame, a row is one record (like a DataFrame row), a column is one field/attribute (like a DataFrame column) and is built to handle millions or billions of rows efficiently without loading everything into the  memory all at once, supports relationships and can be combined on demand via queries.

## 3. What is a Primary Key?
A column (or combination of columns) that uniquely identifies each row in a table. No duplicates allowed, and it can never be null.

## 4. What is a Foreign Key?
A foreign key is a column in one table that references the primary key of another table, creating an explicit link between them.

## 5. What is the difference between WHERE and HAVING?
WHERE is used to fetch specific data according to conditions, for instance i have a table of a super store's data, it has a specific colum named as november_sales, i'll write the query as WHERE november_sales>1000, query will fetch november_sales which are more than 1000 because that was the condition, in short WHERE filters individual rows before any grouping/aggregation happens.
HAVING is like an opposite, it filters groups after aggregation, for instance i have to groupby two columns, until the groupby is not run, HAVING cannot find the results because its whole woking is based on filtering information gained in results of groupby or aggrgation processes.

## 6. What is the difference between ORDER BY and GROUP BY?
ORDER BY just changes the display order of rows/results, no rows are combined, nothing changes about the count of rows returned.
GROUP BY combines rows that share a value into a single summarized row per group, typically used alongside aggregate functions, a completely different operation if compared to ORDER BY, not just a sorting variant.
## 7. What does DISTINCT do?
Removes duplicate rows/values from the result, exactly like .unique() or .drop_duplicates() in Pandas, depending on whether it's applied to one column or a full row.

## 8. When should you use LIMIT?
When we have to preview a small sample of results without pulling back potentially millions of rows, for instance i have a dataset of pixar best movies, i want to see data of first five movies in the dataset, and i use LIMIT, it will give me from start till 5

## 9. What are aggregate functions?
Functions that take many rows and collapse them into a single summary value; COUNT, SUM, AVG, MIN, MAX are the core ones

## 10. Why do Data Scientists prefer databases over Excel for large datasets?
Performance(databases use indexes and query optimization to handle huge data efficiently while Excel loads everything into memory and grinds to a halt past a few hundred thousand rows), reliability (enforced types prevent the kind of silent corruption), collaboration (multiple people and programs can safely read/write simultaneously without file-locking conflicts), and reproducibility (queries are  code like in very easy English wordings version, easy to understand,  controllable and re-runnable. While in manual Excel clicking that's hard to audit or repeat exactly).
