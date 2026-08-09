"""
Phase 3 — NumPy Analysis
RFM segmentation, product similarity, regression (normal equation),
and Monte Carlo stockout simulation — all on raw NumPy arrays.
"""
import numpy as np
import pandas as pd
from . import config


# ---------- RFM ----------
def score_quintile(values: np.ndarray, reverse: bool = False) -> np.ndarray:
    cutoffs = np.percentile(values, [20, 40, 60, 80])
    scores = np.digitize(values, cutoffs) + 1
    if reverse:
        scores = 6 - scores
    return scores


def label_segment(score: int) -> str:
    if score >= 13:
        return "Champions"
    elif score >= 10:
        return "Loyal"
    elif score >= 7:
        return "At Risk"
    else:
        return "Lost"


def compute_rfm(order_items_clean: pd.DataFrame, orders_completed: pd.DataFrame) -> pd.DataFrame:
    order_revenue = order_items_clean.merge(
        orders_completed[["order_id", "customer_id", "order_date"]], on="order_id"
    )
    reference_date = order_revenue["order_date"].max() + pd.Timedelta(days=1)

    rfm = order_revenue.groupby("customer_id").agg(
        last_order_date=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("net_revenue", "sum"),
    ).reset_index()
    rfm["recency"] = (reference_date - rfm["last_order_date"]).dt.days

    rfm["r_score"] = score_quintile(rfm["recency"].to_numpy(), reverse=True)
    rfm["f_score"] = score_quintile(rfm["frequency"].to_numpy())
    rfm["m_score"] = score_quintile(rfm["monetary"].to_numpy())
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]
    rfm["segment"] = rfm["rfm_score"].apply(label_segment)
    return rfm


# ---------- Similarity ----------
def compute_product_similarity(order_items_clean: pd.DataFrame, orders_completed: pd.DataFrame):
    purchases = order_items_clean.merge(orders_completed[["order_id", "customer_id"]], on="order_id")
    purchases = purchases[purchases["quantity"] > 0]

    purchase_matrix = purchases.pivot_table(
        index="customer_id", columns="product_id", values="quantity", aggfunc="sum", fill_value=0
    )
    purchase_array = purchase_matrix.to_numpy()
    product_vectors = purchase_array.T

    dot_products = product_vectors @ product_vectors.T
    norms = np.linalg.norm(product_vectors, axis=1)
    norm_matrix = np.outer(norms, norms)
    norm_matrix[norm_matrix == 0] = 1e-9
    similarity = dot_products / norm_matrix

    return similarity, purchase_matrix


def recommend_products(similarity, purchase_matrix, customer_id, n=3):
    product_ids = purchase_matrix.columns.to_numpy()
    customer_ids = purchase_matrix.index.to_numpy()
    purchase_array = purchase_matrix.to_numpy()

    cust_row = purchase_array[customer_ids == customer_id][0]
    already_bought = set(product_ids[cust_row > 0])
    scores = similarity @ cust_row
    ranked = np.argsort(-scores)

    recs = []
    for idx in ranked:
        pid = product_ids[idx]
        if pid not in already_bought:
            recs.append(pid)
        if len(recs) == n:
            break
    return recs


# ---------- Regression (Normal Equation) ----------
def fit_regression(monthly_revenue_arr: np.ndarray):
    n_months = len(monthly_revenue_arr)
    X_raw = np.arange(n_months).reshape(-1, 1)
    X = np.hstack([np.ones((n_months, 1)), X_raw])
    y = monthly_revenue_arr.reshape(-1, 1)

    beta = np.linalg.inv(X.T @ X) @ X.T @ y
    y_pred = X @ beta
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    return {"beta": beta, "X": X, "X_raw": X_raw, "y": y, "y_pred": y_pred, "r_squared": r_squared}


def forecast_with_interval(fit_result: dict, months_ahead: list):
    X_raw, beta, y, y_pred = fit_result["X_raw"], fit_result["beta"], fit_result["y"], fit_result["y_pred"]
    n, p = fit_result["X"].shape
    residual_var = np.sum((y - y_pred) ** 2) / (n - p)
    x_mean = X_raw.mean()
    Sxx = np.sum((X_raw - x_mean) ** 2)

    rows = []
    for fm in months_ahead:
        x0 = np.array([1, fm])
        point_forecast = (x0 @ beta)[0]
        se_pred = np.sqrt(residual_var * (1 + 1 / n + ((fm - x_mean) ** 2) / Sxx))
        rows.append({
            "month_index": fm, "point_forecast": point_forecast,
            "lower_95": point_forecast - 1.96 * se_pred,
            "upper_95": point_forecast + 1.96 * se_pred,
        })
    return pd.DataFrame(rows)


# ---------- Monte Carlo ----------
def monte_carlo_stockout(order_items_clean, orders_completed, catalog, products, n_trials=None, top_n=5):
    n_trials = n_trials or config.MONTE_CARLO_TRIALS
    catalog = catalog.rename(columns={"SKU": "product_id", "in_stock_units": "stock_units"})

    purchases = order_items_clean.merge(orders_completed[["order_id", "order_date"]], on="order_id")
    purchases = purchases[purchases["quantity"] > 0]
    purchases["month"] = purchases["order_date"].dt.to_period("M")

    monthly_demand = purchases.groupby(["product_id", "month"])["quantity"].sum().reset_index()
    demand_stats = monthly_demand.groupby("product_id")["quantity"].agg(["mean", "std"]).reset_index().dropna()
    demand_stats = demand_stats.merge(catalog[["product_id", "stock_units"]], on="product_id", how="inner")

    np.random.seed(config.RANDOM_SEED)
    rows = []
    for _, r in demand_stats.iterrows():
        sim = np.clip(np.random.normal(r["mean"], r["std"], n_trials), 0, None)
        stockout_prob = (sim > r["stock_units"]).mean()
        se = np.sqrt(stockout_prob * (1 - stockout_prob) / n_trials)
        reorder_point = r["mean"] + 1.65 * r["std"]
        rows.append({
            "product_id": r["product_id"], "stock": r["stock_units"],
            "mean_monthly_demand": round(r["mean"], 1),
            "stockout_probability": round(stockout_prob, 4),
            "ci_95_lower": round(max(0, stockout_prob - 1.96 * se), 4),
            "ci_95_upper": round(min(1, stockout_prob + 1.96 * se), 4),
            "recommended_reorder_point": round(reorder_point, 1),
        })

    results = pd.DataFrame(rows).sort_values("stockout_probability", ascending=False)
    top = results.merge(products[["product_id", "name", "category"]], on="product_id").head(top_n)
    return results, top


def run(cleaned: dict) -> dict:
    """Entry point for this phase. `cleaned` = output of clean.run()."""
    print("[analyze] Computing RFM segmentation...")
    rfm = compute_rfm(cleaned["order_items_clean"], cleaned["orders_completed"])

    print("[analyze] Computing product similarity matrix...")
    similarity, purchase_matrix = compute_product_similarity(
        cleaned["order_items_clean"], cleaned["orders_completed"]
    )
    sample_customers = purchase_matrix.index.to_numpy()[:5]
    recommendations = {
        cid: recommend_products(similarity, purchase_matrix, cid) for cid in sample_customers
    }

    print("[analyze] Fitting regression via normal equation...")
    monthly_revenue = cleaned["category_month_revenue"].sum(axis=0).sort_index().to_numpy()
    fit = fit_regression(monthly_revenue)
    n_months = len(monthly_revenue)
    forecast = forecast_with_interval(fit, [n_months, n_months + 1])

    print("[analyze] Running Monte Carlo stockout simulation...")
    mc_all, mc_top5 = monte_carlo_stockout(
        cleaned["order_items_clean"], cleaned["orders_completed"],
        cleaned["catalog"], cleaned["products_clean"]
    )

    # --- Save Phase 3 outputs ---
    rfm.to_csv(config.PROCESSED / "rfm_segments.csv", index=False)
    mc_all.to_csv(config.PROCESSED / "monte_carlo_all_products.csv", index=False)
    mc_top5.to_csv(config.PROCESSED / "monte_carlo_top5_risk.csv", index=False)
    forecast.to_csv(config.PROCESSED / "revenue_forecast.csv", index=False)
    np.save(config.PROCESSED / "product_similarity_matrix.npy", similarity)
    np.save(config.PROCESSED / "regression_beta.npy", fit["beta"])

    print(f"[analyze] R\u00b2 = {float(fit['r_squared']):.4f}")
    print("[analyze] Phase 3 outputs saved to data/processed/")

    return {
        "rfm": rfm, "similarity": similarity, "purchase_matrix": purchase_matrix,
        "recommendations": recommendations, "fit": fit, "forecast": forecast,
        "monte_carlo_all": mc_all, "monte_carlo_top5": mc_top5,
    }
