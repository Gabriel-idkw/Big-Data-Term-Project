"""
Phase 2 — Cleaning & Integration
Takes the raw tables/CSVs from extract.py and produces clean,
analysis-ready DataFrames, saved to data/processed/.
"""
import numpy as np
import pandas as pd
from . import config

DATE_FORMATS = ["%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y", "%d-%b-%Y"]


def standardize_legacy_dates(legacy: pd.DataFrame) -> pd.DataFrame:
    parsed = pd.Series(pd.NaT, index=legacy.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        attempt = pd.to_datetime(legacy["Signup_Dt"], format=fmt, errors="coerce")
        parsed = parsed.combine_first(attempt)
    legacy = legacy.copy()
    legacy["signup_date"] = parsed
    return legacy


def clean_legacy_customers(legacy: pd.DataFrame) -> pd.DataFrame:
    legacy = standardize_legacy_dates(legacy)
    legacy.columns = legacy.columns.str.strip()
    legacy = legacy.rename(columns={
        "Customer Name": "name", "EMAIL_ADDR": "email",
        "Home City": "city", "Marketing Segment": "segment",
    })

    legacy = legacy.dropna(how="all")
    is_test = legacy["name"].str.contains("test", case=False, na=False) | \
              legacy["email"].str.contains("test", case=False, na=False)
    legacy = legacy[~is_test]

    legacy["name_clean"] = legacy["name"].str.strip().str.title()
    legacy["email_clean"] = legacy["email"].str.strip().str.lower()
    legacy = legacy.sort_values("signup_date").drop_duplicates(subset="email_clean", keep="last")
    return legacy


def apply_missing_value_policy(customers: pd.DataFrame, reviews: pd.DataFrame):
    customers = customers.copy()
    customers["age_was_missing"] = customers["age"].isna()
    customers["age"] = customers["age"].fillna(customers["age"].median())
    customers["city"] = customers["city"].fillna("Unknown")
    customers["gender"] = customers["gender"].fillna("Unknown")

    reviews_with_text = reviews.dropna(subset=["review_text"]).copy()
    return customers, reviews_with_text


def flag_price_outliers(products: pd.DataFrame) -> pd.DataFrame:
    products = products.copy()
    q1, q3 = products["unit_price"].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    products["price_outlier"] = (products["unit_price"] < lower) | (products["unit_price"] > upper)
    return products


def merge_product_catalog(products: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    catalog_clean = catalog.rename(columns={
        "SKU": "product_id", "item_name": "catalog_name", "dept": "catalog_category",
        "list_price_usd": "catalog_price", "supplier_cost": "catalog_cost",
        "in_stock_units": "stock_units",
    })
    merged = products.merge(catalog_clean, on="product_id", how="outer", indicator=True)
    return merged


def clean_order_items(order_items: pd.DataFrame) -> pd.DataFrame:
    content_cols = ["order_id", "product_id", "quantity", "unit_price", "discount"]
    dupe_mask = order_items.duplicated(subset=content_cols, keep="first")
    order_items_clean = order_items[~dupe_mask].copy()
    order_items_clean["is_return"] = order_items_clean["quantity"] < 0
    order_items_clean["net_revenue"] = (
        order_items_clean["unit_price"] * order_items_clean["quantity"] * (1 - order_items_clean["discount"])
    )
    return order_items_clean


def build_category_month_revenue(order_items_clean, orders_completed, products) -> pd.DataFrame:
    # NOTE: joins against orders_completed ONLY — completed orders, not all statuses.
    oi_full = order_items_clean.merge(orders_completed[["order_id", "order_date"]], on="order_id")
    oi_full = oi_full.merge(products[["product_id", "category"]], on="product_id")
    oi_full["order_month"] = oi_full["order_date"].dt.to_period("M").astype(str)
    return oi_full.pivot_table(values="net_revenue", index="category", columns="order_month",
                                aggfunc="sum", fill_value=0)


def build_weekly_active_customers(web_sessions: pd.DataFrame) -> pd.Series:
    ws = web_sessions.set_index("session_date")
    weekly = ws.resample("W")["customer_id"].nunique()
    weekly.name = "active_customers"
    return weekly


def run(raw: dict) -> dict:
    """Entry point for this phase. `raw` = output of extract.run()."""
    print("[clean] Standardizing legacy customer dates & dedup...")
    legacy_clean = clean_legacy_customers(raw["legacy"])

    print("[clean] Applying missing-value policy...")
    customers_clean, reviews_with_text = apply_missing_value_policy(raw["customers"], raw["reviews"])

    print("[clean] Flagging price outliers...")
    products_flagged = flag_price_outliers(raw["products"])

    print("[clean] Merging supplier catalog into products...")
    products_merged = merge_product_catalog(products_flagged, raw["catalog"])

    print("[clean] Cleaning order_items (dedup + return handling)...")
    order_items_clean = clean_order_items(raw["order_items"])

    orders_completed = raw["orders"][raw["orders"]["status"] == "completed"].copy()

    print("[clean] Building category x month revenue matrix...")
    category_month_revenue = build_category_month_revenue(order_items_clean, orders_completed, raw["products"])

    print("[clean] Building weekly active customers time series...")
    weekly_active = build_weekly_active_customers(raw["web_sessions"])

    # --- Save everything Phase 3/4 will read from ---
    customers_clean.to_csv(config.PROCESSED / "clean_customers.csv", index=False)
    legacy_clean.to_csv(config.PROCESSED / "clean_legacy_customers.csv", index=False)
    products_merged.to_csv(config.PROCESSED / "clean_products.csv", index=False)
    order_items_clean.to_csv(config.PROCESSED / "clean_order_items.csv", index=False)
    reviews_with_text.to_csv(config.PROCESSED / "clean_reviews_with_text.csv", index=False)
    raw["reviews"].to_csv(config.PROCESSED / "clean_reviews_full.csv", index=False)
    category_month_revenue.to_csv(config.PROCESSED / "category_month_revenue.csv")
    weekly_active.to_csv(config.PROCESSED / "weekly_active_customers.csv")

    print("[clean] Phase 2 outputs saved to data/processed/")

    return {
        "customers_clean": customers_clean,
        "products_clean": products_flagged,       # plain products + outlier flag (for Phase 3/4 joins)
        "products_merged": products_merged,        # + supplier catalog (for reporting SKU overlap)
        "order_items_clean": order_items_clean,
        "reviews_with_text": reviews_with_text,
        "reviews_full": raw["reviews"],
        "orders": raw["orders"],
        "orders_completed": orders_completed,
        "category_month_revenue": category_month_revenue,
        "weekly_active": weekly_active,
        "web_sessions": raw["web_sessions"],
        "customers_raw": raw["customers"],
        "catalog": raw["catalog"],
    }
