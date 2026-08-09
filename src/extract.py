"""
Phase 1 — Extraction
Loads raw data from the SQLite database and the two external CSVs.
Also runs the 10 required business-question queries from queries.sql
(if that file exists in the project root) and saves each result as a CSV,
so Phase 1's deliverable is reproduced by the same pipeline run.
"""
import sqlite3
import re
import pandas as pd
from . import config


def load_db_tables() -> dict:
    """Loads every core table from ecommerce.db into a dict of DataFrames."""
    con = sqlite3.connect(config.DB_PATH)
    tables = {}
    for name in ["customers", "products", "orders", "order_items", "reviews", "web_sessions"]:
        tables[name] = pd.read_sql(f"SELECT * FROM {name}", con)
    con.close()

    tables["orders"]["order_date"] = pd.to_datetime(tables["orders"]["order_date"])
    tables["web_sessions"]["session_date"] = pd.to_datetime(tables["web_sessions"]["session_date"])
    return tables


def load_external_csvs() -> dict:
    """Loads the legacy customer export and the supplier product catalog."""
    return {
        "legacy": pd.read_csv(config.LEGACY_CSV),
        "catalog": pd.read_csv(config.CATALOG_CSV),
    }


def run_sql_queries(queries_sql_path=None) -> dict:
    """
    Runs each query in queries.sql against the database and saves results
    to data/processed/sql_query_results/. Queries are split on ';' and
    expected to be separated with '-- Query N:' style comments (adjust the
    split logic below if your queries.sql uses a different separator).
    Returns a dict of {query_number: DataFrame} for the queries that ran.
    """
    queries_sql_path = queries_sql_path or (config.PROJECT_ROOT / "queries.sql")
    if not queries_sql_path.exists():
        print(f"[extract] queries.sql not found at {queries_sql_path} — skipping SQL query run.")
        return {}

    out_dir = config.PROCESSED / "sql_query_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_text = queries_sql_path.read_text()
    statements = [s.strip() for s in raw_text.split(";") if s.strip()]

    con = sqlite3.connect(config.DB_PATH)
    results = {}
    for i, stmt in enumerate(statements, start=1):
        try:
            df = pd.read_sql(stmt, con)
            df.to_csv(out_dir / f"query_{i:02d}.csv", index=False)
            results[i] = df
            print(f"[extract] Query {i}: {len(df)} rows -> {out_dir / f'query_{i:02d}.csv'}")
        except Exception as e:
            print(f"[extract] Query {i} failed to run: {e}")
    con.close()
    return results


def run() -> dict:
    """Entry point for this phase — returns everything downstream phases need."""
    print("[extract] Loading database tables...")
    db_tables = load_db_tables()
    print("[extract] Loading external CSVs...")
    csvs = load_external_csvs()
    print("[extract] Running SQL queries (Phase 1 deliverable)...")
    run_sql_queries()

    return {**db_tables, **csvs}
