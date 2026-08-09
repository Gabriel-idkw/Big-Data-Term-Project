"""
Phase 4 — Business Insights & Visualization
Produces one chart per business question, saved to figures/,
plus a text summary of the key numbers for each answer.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker
from . import config

sns.set_style("whitegrid")


def q1_segment_revenue(rfm: pd.DataFrame, customers_clean: pd.DataFrame) -> dict:
    segment_revenue = rfm.groupby("segment")["monetary"].sum().sort_values(ascending=False)
    rfm_demo = rfm.merge(customers_clean, on="customer_id")
    demo = rfm_demo.groupby("segment").agg(
        avg_age=("age", "mean"),
        top_country=("country", lambda x: x.mode()[0] if not x.mode().empty else None),
        pct_female=("gender", lambda x: (x == "F").mean()),
    ).round(2)

    fig, ax = plt.subplots(figsize=(8, 5))
    segment_revenue.plot(kind="bar", ax=ax, color=sns.color_palette("viridis", len(segment_revenue)))
    ax.set_title("Total Revenue by RFM Segment")
    ax.set_ylabel("Revenue ($)")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q1_segment_revenue.png", dpi=150)
    plt.close(fig)

    return {"segment_revenue": segment_revenue.to_dict(), "demographics": demo.to_dict()}


def q2_seasonality(category_month_revenue: pd.DataFrame) -> dict:
    monthly_revenue = category_month_revenue.sum(axis=0).sort_index()
    monthly_revenue.index = pd.to_datetime(monthly_revenue.index)
    rolling_avg = monthly_revenue.rolling(window=3).mean()

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(monthly_revenue.index, monthly_revenue.values, marker="o", markersize=4,
            color="#4C72B0", linewidth=1, alpha=0.45, label="Monthly Revenue", zorder=1)
    ax.plot(rolling_avg.index, rolling_avg.values, linewidth=2.5, color="darkred",
            label="3-Month Rolling Average", zorder=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_ylim(bottom=0)
    peak_idx = monthly_revenue.idxmax()
    trough_idx = monthly_revenue.idxmin()
    ax.annotate(f"${monthly_revenue[peak_idx]:,.0f}",
                xy=(peak_idx, monthly_revenue[peak_idx]),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=9, fontweight="bold", color="#2c5aa0")
    ax.annotate(f"${monthly_revenue[trough_idx]:,.0f}",
                xy=(trough_idx, monthly_revenue[trough_idx]),
                xytext=(0, -15), textcoords="offset points",
                ha="center", fontsize=9, fontweight="bold", color="#2c5aa0")
    ax.set_xticks(monthly_revenue.index)
    ax.set_xticklabels([d.strftime("%Y-%m") for d in monthly_revenue.index], rotation=45, ha="right", fontsize=8)

    ax.set_title("Monthly Revenue with Rolling Average (Seasonality Check)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Revenue ($)", fontsize=11)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(config.FIGURES / "q2_seasonality.png", dpi=150)
    plt.close(fig)

    mrdf = monthly_revenue.reset_index()
    mrdf.columns = ["month", "revenue"]
    mrdf["calendar_month"] = mrdf["month"].dt.month_name()
    seasonal_avg = mrdf.groupby("calendar_month")["revenue"].mean().sort_values(ascending=False)
    return {"seasonal_avg_by_month": seasonal_avg.to_dict()}


def q3_margin(order_items_clean: pd.DataFrame, products_clean: pd.DataFrame) -> dict:
    oi = order_items_clean.merge(products_clean[["product_id", "category", "cost"]], on="product_id")
    oi["net_cost"] = oi["quantity"] * oi["cost"]
    cat_margin = oi.groupby("category").agg(net_revenue=("net_revenue", "sum"), net_cost=("net_cost", "sum"))
    cat_margin["effective_margin_pct"] = (
        (cat_margin["net_revenue"] - cat_margin["net_cost"]) / cat_margin["net_revenue"]
    ) * 100
    cat_margin = cat_margin.sort_values("effective_margin_pct", ascending=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    cat_margin["effective_margin_pct"].plot(kind="barh", ax=ax,
                                             color=sns.color_palette("crest", len(cat_margin)))
    ax.set_title("Effective Margin % by Category (After Discounts & Returns)")
    ax.set_xlabel("Effective Margin (%)")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q3_margin.png", dpi=150)
    plt.close(fig)

    return {"category_margin_pct": cat_margin["effective_margin_pct"].to_dict()}


def q4_rating_vs_repeat(rfm: pd.DataFrame, reviews_full: pd.DataFrame) -> dict:
    avg_rating = reviews_full.groupby("customer_id")["rating"].mean().reset_index()
    avg_rating.columns = ["customer_id", "avg_rating"]
    merged = rfm[["customer_id", "frequency"]].merge(avg_rating, on="customer_id")
    merged["is_repeat_purchaser"] = merged["frequency"] > 1

    correlation = np.corrcoef(merged["avg_rating"].to_numpy(), merged["frequency"].to_numpy())[0, 1]
    comparison = merged.groupby("is_repeat_purchaser")["avg_rating"].mean()

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.boxplot(data=merged, x="is_repeat_purchaser", y="avg_rating", ax=ax)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["One-time buyer", "Repeat buyer"])
    ax.set_title("Average Review Rating: One-time vs Repeat Buyers")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q4_rating_repeat.png", dpi=150)
    plt.close(fig)

    return {"correlation": correlation, "avg_rating_by_group": comparison.to_dict()}


def q5_device_country_conversion(web_sessions: pd.DataFrame, customers_clean: pd.DataFrame,
                                   orders_completed: pd.DataFrame, min_customers=20) -> dict:
    sessions = web_sessions.merge(customers_clean[["customer_id", "country"]], on="customer_id")
    purchasers = set(orders_completed["customer_id"])

    dc = sessions.groupby(["device", "country"])["customer_id"].apply(
        lambda ids: pd.Series({"session_customers": ids.nunique(), "purchasers": len(set(ids) & purchasers)})
    ).unstack()
    dc["conversion_rate"] = dc["purchasers"] / dc["session_customers"]
    dc_filtered = dc[dc["session_customers"] >= min_customers].sort_values("conversion_rate", ascending=False)

    top10 = dc_filtered.head(10).reset_index()
    top10["label"] = top10["device"] + " / " + top10["country"]

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=top10, y="label", x="conversion_rate", ax=ax, hue="label", palette="flare", legend=False)
    ax.set_title("Top 10 Device x Country Combinations by Conversion Rate")
    ax.set_xlabel("Conversion Rate")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q5_conversion.png", dpi=150)
    plt.close(fig)

    return {"top_combinations": top10.to_dict(orient="records")}


def q6_forecast(fit: dict, forecast: pd.DataFrame) -> dict:
    monthly_revenue_arr = fit["y"].flatten()
    y_pred = fit["y_pred"].flatten()
    n_months = len(monthly_revenue_arr)
    future_x = forecast["month_index"].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Actual revenue: keep this the most visually dominant line
    ax.plot(range(n_months), monthly_revenue_arr, marker="o", markersize=5,
            color="#4C72B0", linewidth=1.8, label="Historical Revenue", zorder=3)

    # Fitted trend: lighter, thinner, drawn BEHIND the actual line so it reads
    # as a background reference rather than competing for attention
    ax.plot(range(n_months), y_pred, linestyle="--", color="gray",
            linewidth=1.3, alpha=0.6, label="Fitted Trend", zorder=1)

    # Forecast: distinct color, connected to the last historical point for continuity
    connect_x = [n_months - 1] + list(future_x)
    connect_y = [monthly_revenue_arr[-1]] + list(forecast["point_forecast"])
    ax.plot(connect_x, connect_y, marker="o", markersize=6, color="darkred",
            linewidth=2, label="Forecast", zorder=3)

    ax.fill_between(future_x, forecast["lower_95"], forecast["upper_95"],
                     color="darkred", alpha=0.15, label="95% Prediction Interval", zorder=2)

    # Vertical line marking where history ends and forecast begins
    ax.axvline(x=n_months - 1, color="black", linestyle=":", linewidth=1, alpha=0.5)
    ax.set_title("Revenue Forecast: Next 2 Months")
    ax.set_xlabel("Month Index")
    ax.set_ylabel("Revenue ($)")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q6_forecast.png", dpi=150)
    plt.close(fig)

    return {"r_squared": float(fit["r_squared"]), "forecast": forecast.to_dict(orient="records")}


def q7_stockout_risk(mc_top5: pd.DataFrame) -> dict:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=mc_top5, y="name", x="stockout_probability", ax=ax, hue="name", palette="rocket", legend=False)
    ax.set_title("Top 5 Stockout-Risk Products (Monte Carlo, 5,000 trials)")
    ax.set_xlabel("Stockout Probability")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q7_stockout.png", dpi=150)
    plt.close(fig)
    return {"top5_stockout_risk": mc_top5.to_dict(orient="records")}


def q8_data_quality(order_items_clean: pd.DataFrame, orders: pd.DataFrame, orders_completed: pd.DataFrame) -> dict:
    oi_naive = order_items_clean.merge(orders[["order_id", "status"]], on="order_id")
    oi_naive["naive_revenue"] = oi_naive["unit_price"] * oi_naive["quantity"] * (1 - oi_naive["discount"])
    naive_total = oi_naive["naive_revenue"].sum()
    cleaned_total = order_items_clean.merge(orders_completed[["order_id"]], on="order_id")["net_revenue"].sum()
    pct_overstatement = (naive_total - cleaned_total) / cleaned_total * 100

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(["Naive (all statuses)", "Cleaned (completed only)"], [naive_total, cleaned_total],
           color=["indianred", "seagreen"])
    ax.set_title("Revenue: Before vs. After Data Cleaning")
    ax.set_ylabel("Total Revenue ($)")
    plt.tight_layout()
    plt.savefig(config.FIGURES / "q8_dataquality.png", dpi=150)
    plt.close(fig)

    return {"naive_total": naive_total, "cleaned_total": cleaned_total, "pct_overstatement": pct_overstatement}


def run(cleaned: dict, analyzed: dict) -> dict:
    """Entry point for this phase. Runs all 8 questions, saves charts + a JSON summary."""
    print("[visualize] Q1 — segment revenue...")
    q1 = q1_segment_revenue(analyzed["rfm"], cleaned["customers_clean"])
    print("[visualize] Q2 — seasonality...")
    q2 = q2_seasonality(cleaned["category_month_revenue"])
    print("[visualize] Q3 — margin by category...")
    q3 = q3_margin(cleaned["order_items_clean"], cleaned["products_clean"])
    print("[visualize] Q4 — rating vs repeat purchase...")
    q4 = q4_rating_vs_repeat(analyzed["rfm"], cleaned["reviews_full"])
    print("[visualize] Q5 — device x country conversion...")
    q5 = q5_device_country_conversion(cleaned["web_sessions"], cleaned["customers_clean"], cleaned["orders_completed"])
    print("[visualize] Q6 — revenue forecast...")
    q6 = q6_forecast(analyzed["fit"], analyzed["forecast"])
    print("[visualize] Q7 — stockout risk...")
    q7 = q7_stockout_risk(analyzed["monte_carlo_top5"])
    print("[visualize] Q8 — data quality finding...")
    q8 = q8_data_quality(cleaned["order_items_clean"], cleaned["orders"], cleaned["orders_completed"])

    summary = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6, "q7": q7, "q8": q8}

    import json
    def default(o):
        if isinstance(o, (np.integer, np.floating)):
            return float(o)
        return str(o)
    with open(config.PROCESSED / "phase4_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=default)

    print("[visualize] All 8 charts saved to figures/, summary saved to data/processed/phase4_summary.json")
    return summary
