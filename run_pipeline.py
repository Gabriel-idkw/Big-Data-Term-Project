"""
UrbanCart Term Project — Full Pipeline Driver
Runs Phases 1-4 end to end: raw files -> clean data -> analysis -> charts.

Usage:
    python run_pipeline.py

Requires:
    data/raw/ecommerce.db
    data/raw/legacy_customers_export.csv
    data/raw/product_catalog_2024.csv
    (optional) queries.sql in the project root, for the Phase 1 SQL deliverable
"""
import time
from src import extract, clean, analyze, visualize


def main():
    start = time.time()
    print("=" * 60)
    print("UrbanCart Pipeline — starting")
    print("=" * 60)

    print("\n--- PHASE 1: Extraction ---")
    raw = extract.run()

    print("\n--- PHASE 2: Cleaning & Integration ---")
    cleaned = clean.run(raw)

    print("\n--- PHASE 3: NumPy Analysis ---")
    analyzed = analyze.run(cleaned)

    print("\n--- PHASE 4: Business Insights & Visualization ---")
    summary = visualize.run(cleaned, analyzed)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"Pipeline complete in {elapsed:.1f}s")
    print("Outputs:")
    print("  - data/processed/  (cleaned tables + analysis results)")
    print("  - figures/         (all 8 charts)")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    main()
