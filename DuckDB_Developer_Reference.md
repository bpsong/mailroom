# 🐥 DuckDB Developer Reference (Offline Markdown)

A compact, developer-focused reference for using **DuckDB** as an embedded database in Python or local applications.  
Ideal for offline AI assistants or developers integrating DuckDB into FastAPI, Flask, Streamlit, or automation workflows.

---

## 🧭 1. Overview

**DuckDB** is an **embedded analytical SQL database**.  
It’s like SQLite but optimized for analytics — columnar, vectorized, and multi-threaded.

### Core Principles
- Runs **in-process** — no server required.
- **Columnar storage** for high-speed analytics.
- **SQL interface** — supports complex joins, CTEs, and window functions.
- **ACID** compliant (via MVCC — Multi-Version Concurrency Control).
- Reads and writes **Parquet, CSV, JSON, Arrow**, etc.
- Great interoperability with **Pandas**, **Polars**, **Arrow**, and **NumPy**.

### Common Use Cases
- Analytics engine inside local apps or APIs.
- Local data warehouse for offline apps.
- Fast SQL layer on top of Pandas/Arrow data.
- ETL/ELT jobs, dashboards, and data prep.
- Embedded DB for AI assistants & dev tools.

---

## ⚙️ 2. Installation & Setup

### 🧩 Python
```bash
pip install duckdb
```
Optionally install with Arrow/Pandas support:
```bash
pip install duckdb[parquet,pandas]
```

### 🖥️ CLI
```bash
duckdb mydata.duckdb
```
or ephemeral session:
```bash
duckdb :memory:
```

### 🧠 Quick test
```python
import duckdb
con = duckdb.connect()
print(con.execute("SELECT 42").fetchall())
```

---

## 🐍 3. Python API Basics

### Connect / Create Database
```python
import duckdb
con = duckdb.connect("mailroom.duckdb")   # or ":memory:" for ephemeral
```

### Execute SQL
```python
con.execute("CREATE TABLE users(id INTEGER, name TEXT)")
con.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
result = con.execute("SELECT * FROM users").fetchall()
print(result)
```

### Return as Pandas DataFrame
```python
df = con.execute("SELECT * FROM users").fetchdf()
```

### Parameter Binding
```python
con.execute("INSERT INTO users VALUES (?, ?)", [3, 'Charlie'])
```

### Using DataFrames Directly
```python
import pandas as pd
df = pd.DataFrame({'x': [1,2,3]})
con.register("df_view", df)
print(con.execute("SELECT AVG(x) FROM df_view").fetchone())
```

### Registering & Unregistering Tables
```python
con.register("temp_table", df)
con.unregister("temp_table")
```

### Persist Database
DuckDB stores data in a single `.duckdb` file:
```python
con = duckdb.connect("mailroom.duckdb")
con.execute("CREATE TABLE logs AS SELECT * FROM read_csv_auto('logs.csv')")
```

---

## 📦 4. File I/O and Formats

### CSV
```sql
CREATE TABLE sales AS SELECT * FROM read_csv_auto('sales.csv');
COPY sales TO 'backup.csv' (HEADER, DELIMITER ',');
```

### Parquet
```sql
SELECT * FROM read_parquet('data/*.parquet');
COPY (SELECT * FROM sales) TO 'sales.parquet' (FORMAT PARQUET);
```

### JSON
```sql
SELECT * FROM read_json('data.json');
```

### Arrow / Pandas Integration
DuckDB can read Arrow tables or Pandas DataFrames directly via the Python API.

---

## 🧮 5. SQL Commands (Core Reference)

### Data Definition (DDL)
```sql
CREATE TABLE packages (
  id INTEGER PRIMARY KEY,
  tracking_no TEXT,
  recipient TEXT,
  status TEXT,
  created_at TIMESTAMP
);

ALTER TABLE packages ADD COLUMN notes TEXT;
DROP TABLE IF EXISTS temp;
```

### Data Manipulation (DML)
```sql
INSERT INTO packages VALUES (1, 'SG12345', 'Jane', 'registered', now());
UPDATE packages SET status='delivered' WHERE id=1;
DELETE FROM packages WHERE status='returned';
```

### Querying Data
```sql
SELECT recipient, COUNT(*) FROM packages
WHERE status='delivered'
GROUP BY recipient
ORDER BY COUNT(*) DESC;
```

### Joins & Subqueries
```sql
SELECT p.id, r.department
FROM packages p
JOIN recipients r ON p.recipient = r.name;
```

### Common Table Expressions (CTEs)
```sql
WITH recent AS (
  SELECT * FROM packages WHERE created_at > now() - INTERVAL 7 DAY
)
SELECT status, COUNT(*) FROM recent GROUP BY status;
```

### Window Functions
```sql
SELECT
  recipient,
  COUNT(*) OVER (PARTITION BY status) AS status_total
FROM packages;
```

---

## 🔌 6. Extensions

### Install / Load Extensions
```sql
INSTALL 'httpfs';
LOAD 'httpfs';
```
Available extensions:  
- `httpfs` (remote files via HTTPS/S3)  
- `json` (JSON table functions)  
- `sqlite_scanner` (read SQLite DBs)  
- `excel` (read/write .xlsx)  
- `inet`, `tpch`, `fts`, etc.

### Example — Read remote Parquet file
```sql
INSTALL httpfs;
LOAD httpfs;
SELECT * FROM read_parquet('https://example.com/data.parquet');
```

---

## ⚙️ 7. Configuration (PRAGMAs)

```sql
PRAGMA threads=4;
PRAGMA memory_limit='4GB';
PRAGMA temp_directory='C:\temp\duckdb_tmp';
PRAGMA enable_progress_bar;
```

### Check All Settings
```sql
SELECT * FROM duckdb_settings();
```

---

## 🧠 8. Integration Patterns

### Embedding in FastAPI / Flask
```python
from fastapi import FastAPI
import duckdb

app = FastAPI()
con = duckdb.connect("mailroom.duckdb")

@app.get("/packages")
def list_packages():
    df = con.execute("SELECT * FROM packages").fetchdf()
    return df.to_dict(orient="records")
```

---

## ⚡ 9. Performance Tips

| Tip | Explanation |
|------|--------------|
| Use **Parquet** instead of CSV for big data | Columnar compression & faster read. |
| Avoid many small commits | Batch inserts with `executemany` or `COPY`. |
| Serialize writes | DuckDB supports one writer at a time. |
| Use CTEs for readability | They compile efficiently. |
| Use `EXPLAIN` | Analyze query plan for tuning. |

---

## 🔒 10. Transactions & Concurrency

- Supports **ACID** transactions.
- Only **one writer** at a time, but many readers.
- Writes are atomic; failed writes auto-rollback.

Example:
```python
with con:
    con.execute("INSERT INTO logs VALUES (1, 'entry')")
```

---

## 🧩 11. Developer Quick Commands

| Task | Command |
|------|----------|
| Create new DB | `duckdb mydb.duckdb` |
| List tables | `SHOW TABLES;` |
| Schema info | `.schema` |
| Run query | `.mode csv
SELECT * FROM table;` |
| Export | `COPY (SELECT * FROM table) TO 'out.csv' (HEADER);` |

---

**End of DuckDB Developer Reference (Offline Markdown)**
