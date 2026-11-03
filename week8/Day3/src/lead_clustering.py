"""Week 8 Day 3: Customer Persona Discovery via Unsupervised K-Means Clustering.

Discovers actionable real estate buyer personas:
1. High-Net-Worth / Overseas Investor
2. Serious First-Time Homebuyer
3. Budget Urban Renter
4. Casual Window Shopper / Speculator

Outputs:
- Cluster profile table (mean budget, engagement, conversion rate, preferred property types)
- Multi-dimensional visualization (Scatter & Radar profile plot)
- Reusable fitted pipeline in models/kmeans_customer_personas.joblib
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

DAY3_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = DAY3_DIR / "reports" / "figures"
REPORTS_DIR = DAY3_DIR / "reports"
MODELS_DIR = DAY3_DIR / "models"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def discover_customer_personas(
    train_df: pd.DataFrame,
    n_clusters: int = 4,
    random_state: int = 42
) -> Tuple[pd.DataFrame, Dict[int, str], KMeans, StandardScaler]:
    """Fits K-Means on behavioral & intent features, assigns human-readable personas,
    and returns cluster profile statistics.
    """
    df = train_df.copy()

    # Features for persona segmentation
    feature_cols = [
        "budget_pkr",
        "number_of_calls",
        "avg_call_duration_mins",
        "response_time_hours",
        "days_since_first_contact",
        "lead_engagement_score",
        "budget_to_market_ratio",
    ]

    # Preprocess
    X = df[feature_cols].copy()
    X["is_buy"] = (df["purpose"] == "Buy").astype(int)
    X["visit_booked_num"] = (df["visit_booked"] == "Yes").astype(int)
    X["is_commercial_or_plot"] = df["property_type"].isin(["Commercial", "Plot"]).astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Fit K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    df["cluster"] = clusters

    # Profile clusters
    profile_df = df.groupby("cluster").agg(
        total_leads=("lead_id", "count"),
        mean_budget_pkr=("budget_pkr", "mean"),
        median_budget_pkr=("budget_pkr", "median"),
        mean_calls=("number_of_calls", "mean"),
        mean_call_duration=("avg_call_duration_mins", "mean"),
        mean_response_time_hrs=("response_time_hours", "mean"),
        visit_booked_rate=("visit_booked", lambda s: np.mean(s == "Yes")),
        buy_purpose_rate=("purpose", lambda s: np.mean(s == "Buy")),
        actual_conversion_rate=("converted_binary", "mean"),
    ).reset_index()

    # Intelligently map clusters to personas based on budget and buy purpose
    persona_map = {}
    for idx, row in profile_df.iterrows():
        c_id = int(row["cluster"])
        budget_cr = row["mean_budget_pkr"] / 1e7
        buy_pct = row["buy_purpose_rate"]
        visit_pct = row["visit_booked_rate"]

        if buy_pct < 0.30 or budget_cr < 0.20:
            persona_map[c_id] = "Budget Urban Renter"
        elif budget_cr >= 2.5:
            persona_map[c_id] = "High-Net-Worth / Overseas Investor"
        elif visit_pct >= 0.35 or row["mean_calls"] >= 2.8:
            persona_map[c_id] = "Serious First-Time Homebuyer"
        else:
            persona_map[c_id] = "Casual Window Shopper / Speculator"

    profile_df["persona_title"] = profile_df["cluster"].map(persona_map)
    profile_df["mean_budget_display"] = profile_df["mean_budget_pkr"].apply(
        lambda b: f"{b/1e7:.2f} Cr PKR" if b >= 1e7 else f"{b/1e5:.1f} Lac PKR"
    )

    # Save artifact
    profile_df.to_csv(REPORTS_DIR / "customer_personas_summary.csv", index=False)

    # Save model
    cluster_artifacts = {
        "kmeans": kmeans,
        "scaler": scaler,
        "feature_cols": X.columns.tolist(),
        "persona_map": persona_map,
        "n_clusters": n_clusters
    }
    joblib.dump(cluster_artifacts, MODELS_DIR / "kmeans_customer_personas.joblib")

    # Plot Visualizations
    plot_personas(X_scaled, clusters, profile_df, persona_map)

    return profile_df, persona_map, kmeans, scaler


def plot_personas(
    X_scaled: np.ndarray,
    clusters: np.ndarray,
    profile_df: pd.DataFrame,
    persona_map: Dict[int, str],
    save_path: Path = FIGURES_DIR / "04_customer_personas_clustering.png"
):
    """Visualizes 2D PCA projection of personas and behavioral metrics comparison."""
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), dpi=300)

    # 1. PCA Scatter Plot
    palette = sns.color_palette("Set2", len(persona_map))
    for c_id, color in zip(sorted(persona_map.keys()), palette):
        mask = (clusters == c_id)
        axes[0].scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            label=f"{persona_map[c_id]} (N={np.sum(mask)})",
            color=color, alpha=0.6, edgecolors="none", s=35
        )

    axes[0].set_title("Customer Personas in 2D Latent Space (PCA Projection)", fontsize=13, fontweight="bold", pad=10)
    axes[0].set_xlabel(f"Principal Component 1 ({pca.explained_variance_ratio_[0]:.1%} variance)", fontsize=11)
    axes[0].set_ylabel(f"Principal Component 2 ({pca.explained_variance_ratio_[1]:.1%} variance)", fontsize=11)
    axes[0].legend(loc="upper right", frameon=True, fontsize=9)

    # 2. Conversion & Visit Rates by Persona Bar Chart
    df_sorted = profile_df.sort_values(by="actual_conversion_rate", ascending=False)
    x = np.arange(len(df_sorted))
    width = 0.35

    ax_bar = axes[1]
    ax_bar.bar(x - width/2, df_sorted["actual_conversion_rate"] * 100, width, label="Conversion Rate (%)", color="#2ca02c")
    ax_bar.bar(x + width/2, df_sorted["visit_booked_rate"] * 100, width, label="Visit Booked Rate (%)", color="#1f77b4")

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(df_sorted["persona_title"], rotation=20, ha="right", fontsize=10, fontweight="bold")
    ax_bar.set_ylabel("Rate (%)", fontsize=11)
    ax_bar.set_title("Actual Conversion & In-Person Visit Rates by Persona", fontsize=13, fontweight="bold", pad=10)
    ax_bar.legend(loc="upper right", frameon=True)
    ax_bar.set_ylim([0, 80])

    plt.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Customer Personas figure: {save_path}")
