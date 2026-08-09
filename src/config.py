"""
Central place for paths and constants used across the pipeline.
Import from here instead of hardcoding paths in every module.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

DB_PATH = RAW / "ecommerce.db"
LEGACY_CSV = RAW / "legacy_customers_export.csv"
CATALOG_CSV = RAW / "product_catalog_2024.csv"

# Make sure output folders exist whenever config is imported
PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
MONTE_CARLO_TRIALS = 5000
