"""Week 8 Day 3: Lead Scoring Evaluation, Calibration, and Business Cost Analysis.

Implements:
1. ROC-AUC and PR-AUC curve plotting and metric computation
2. Precision@Top-20% and Lift Curve computation
3. Calibration Curves (Reliability Diagrams) and Brier Score evaluation
4. Business Cost Curve: Cost(t) = FN(t)*C_FN + FP(t)*C_FP
5. Disparate Impact and Fairness / Bias audit across City and Lead Source
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import CalibrationDisplay, calibration_curve
from sklearn.metrics import (
    auc, average_precision_score, confusion_matrix,
    precision_recall_curve, roc_curve, brier_score_loss
)

DAY3_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = DAY3_DIR / "reports" / "figures"
REPORTS_DIR = DAY3_DIR / "reports"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Set publication style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10


def plot_roc_and_pr_curves(
    models_dict: Dict[str, Any],
    X_test: np.ndarray,
    y_test: np.ndarray,
    save_path: Path = FIGURES_DIR / "01_imbalance_and_model_roc_pr_curves.png"
):
    """Plots multi-model ROC Curves and Precision-Recall Curves side-by-side."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), dpi=300)

    palette = sns.color_palette("tab10", len(models_dict))

    # 1. ROC Curves
    ax_roc = axes[0]
    ax_roc.plot([0, 1], [0, 1], "k--", alpha=0.6, label="Random Guess (AUC = 0.50)")

    # 2. PR Curves
    ax_pr = axes[1]
    base_rate = np.mean(y_test)
    ax_pr.plot([0, 1], [base_rate, base_rate], "k--", alpha=0.6, label=f"Base Rate ({base_rate:.1%})")

    for (name, model), color in zip(models_dict.items(), palette):
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)[:, 1]
        else:
            y_proba = model.predict(X_test)

        # ROC
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        roc_auc = auc(fpr, tpr)
        ax_roc.plot(fpr, tpr, label=f"{name} (AUC = {roc_auc:.3f})", color=color, lw=2)

        # PR
        prec, rec, _ = precision_recall_curve(y_test, y_proba)
        pr_auc = average_precision_score(y_test, y_proba)
        ax_pr.plot(rec, prec, label=f"{name} (PR-AUC = {pr_auc:.3f})", color=color, lw=2)

    ax_roc.set_title("ROC Curves Comparison (Lead Conversion)", fontsize=13, fontweight="bold", pad=10)
    ax_roc.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    ax_roc.set_ylabel("True Positive Rate (Recall)", fontsize=11)
    ax_roc.legend(loc="lower right", frameon=True, fontsize=9)
    ax_roc.set_xlim([0, 1])
    ax_roc.set_ylim([0, 1.02])

    ax_pr.set_title("Precision-Recall Curves (Class Imbalance Focus)", fontsize=13, fontweight="bold", pad=10)
    ax_pr.set_xlabel("Recall (Fraction of Converted Leads Caught)", fontsize=11)
    ax_pr.set_ylabel("Precision (Accuracy of Call Outreach)", fontsize=11)
    ax_pr.legend(loc="upper right", frameon=True, fontsize=9)
    ax_pr.set_xlim([0, 1])
    ax_pr.set_ylim([0, 1.02])

    plt.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved ROC and PR curves: {save_path}")


def plot_confusion_and_calibration(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    threshold: float = 0.50,
    save_path: Path = FIGURES_DIR / "02_confusion_matrices_and_calibration.png"
):
    """Plots Confusion Matrix and Probability Calibration Curve for the primary lead scoring model."""
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    cm = confusion_matrix(y_test, y_pred)
    cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), dpi=300)

    # 1. Confusion Matrix
    ax_cm = axes[0]
    labels = np.array([
        [f"True Neg (TN)\n{cm[0,0]}\n({cm_norm[0,0]:.1%})", f"False Pos (FP)\n{cm[0,1]}\n({cm_norm[0,1]:.1%})"],
        [f"False Neg (FN)\n{cm[1,0]}\n({cm_norm[1,0]:.1%})", f"True Pos (TP)\n{cm[1,1]}\n({cm_norm[1,1]:.1%})"],
    ])
    sns.heatmap(cm, annot=labels, fmt="", cmap="Blues", cbar=False, ax=ax_cm,
                xticklabels=["Not Converted (0)", "Converted (1)"],
                yticklabels=["Not Converted (0)", "Converted (1)"],
                annot_kws={"size": 11, "weight": "bold"})
    ax_cm.set_title(f"Confusion Matrix (Decision Threshold t = {threshold:.2f})", fontsize=13, fontweight="bold", pad=10)
    ax_cm.set_xlabel("Predicted Label", fontsize=11)
    ax_cm.set_ylabel("True Actual Outcome", fontsize=11)

    # 2. Calibration Curve
    ax_cal = axes[1]
    prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=8, strategy="uniform")
    brier = brier_score_loss(y_test, y_proba)

    ax_cal.plot([0, 1], [0, 1], "k--", label="Perfect Calibration (Ideal)", alpha=0.7)
    ax_cal.plot(prob_pred, prob_true, "s-", color="#1f77b4", lw=2, markersize=7,
                label=f"LightGBM (Brier Score = {brier:.4f})")
    ax_cal.set_title("Probability Calibration Curve (Reliability Diagram)", fontsize=13, fontweight="bold", pad=10)
    ax_cal.set_xlabel("Mean Predicted Conversion Probability", fontsize=11)
    ax_cal.set_ylabel("Empirical Fraction of Positives (True Conversion)", fontsize=11)
    ax_cal.set_xlim([0, 1])
    ax_cal.set_ylim([0, 1])
    ax_cal.legend(loc="lower right", frameon=True)

    plt.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Confusion Matrix and Calibration plot: {save_path}")


def analyze_business_cost_curve(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    cost_fn: float = 400000.0,  # Lost commission from missing a hot lead (PKR 4 Lac)
    cost_fp: float = 1200.0,    # Wasted sales agent call time (15 mins + overhead in PKR)
    save_path: Path = FIGURES_DIR / "03_business_cost_threshold_curve.png"
) -> Tuple[float, float, pd.DataFrame]:
    """Computes total expected business loss across decision thresholds t in [0.05, 0.95].
    Cost(t) = FN(t) * cost_fn + FP(t) * cost_fp
    """
    y_proba = model.predict_proba(X_test)[:, 1]
    thresholds = np.linspace(0.05, 0.95, 91)

    records = []
    for t in thresholds:
        preds = (y_proba >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
        loss = (fn * cost_fn) + (fp * cost_fp)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        records.append({
            "threshold": t,
            "FN": fn,
            "FP": fp,
            "TP": tp,
            "TN": tn,
            "cost_pkr_millions": loss / 1e6,
            "precision": prec,
            "recall": rec,
            "f1": f1
        })

    df_cost = pd.DataFrame(records)
    best_idx = df_cost["cost_pkr_millions"].idxmin()
    best_thresh = float(df_cost.loc[best_idx, "threshold"])
    min_cost = float(df_cost.loc[best_idx, "cost_pkr_millions"])

    # Standard threshold 0.50 comparison
    cost_at_50 = float(df_cost.loc[np.abs(df_cost["threshold"] - 0.50).argmin(), "cost_pkr_millions"])
    savings = (cost_at_50 - min_cost)

    # Plot
    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)

    color_cost = "#d62728"
    ax1.plot(df_cost["threshold"], df_cost["cost_pkr_millions"], color=color_cost, lw=2.5, label="Total Cost (PKR Millions)")
    ax1.axvline(best_thresh, color=color_cost, linestyle="--", alpha=0.8,
                label=f"Cost-Minimizing t* = {best_thresh:.2f} (PKR {min_cost:.2f}M)")
    ax1.axvline(0.50, color="gray", linestyle=":", alpha=0.8,
                label=f"Default Threshold 0.50 (PKR {cost_at_50:.2f}M)")
    ax1.set_xlabel("Decision Threshold (Probability of Conversion)", fontsize=11)
    ax1.set_ylabel("Total Business Cost (Million PKR)", color=color_cost, fontsize=11)
    ax1.tick_params(axis="y", labelcolor=color_cost)

    # Second axis for F1 and Recall
    ax2 = ax1.twinx()
    color_rec = "#1f77b4"
    color_f1 = "#2ca02c"
    ax2.plot(df_cost["threshold"], df_cost["recall"], color=color_rec, linestyle="-.", lw=1.8, label="Recall (Hot Leads Caught)")
    ax2.plot(df_cost["threshold"], df_cost["f1"], color=color_f1, linestyle="-", lw=1.8, label="F1 Score")
    ax2.set_ylabel("Metric Score", color="#333333", fontsize=11)
    ax2.set_ylim([0, 1.05])

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center left", frameon=True, fontsize=9)

    plt.title(f"Business Cost vs Decision Threshold (Missing Lead: PKR 400k vs Wasted Call: PKR 1.2k)\n"
              f"Cost-Optimal Threshold t*={best_thresh:.2f} saves PKR {savings:.2f} Million vs Default 0.50!",
              fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Business Cost Optimization curve: {save_path}")

    return best_thresh, cost_at_50 - min_cost, df_cost


def audit_fairness_and_bias(
    test_df: pd.DataFrame,
    y_proba: np.ndarray,
    threshold: float = 0.40,
    save_path: Path = FIGURES_DIR / "09_fairness_and_bias_audit.png"
) -> pd.DataFrame:
    """Audits model predictions for disparate impact and parity across City and Lead Source."""
    df_eval = test_df.copy()
    df_eval["y_proba"] = y_proba
    df_eval["y_pred"] = (y_proba >= threshold).astype(int)
    y_true = df_eval["converted_binary"].to_numpy()

    # 1. By City
    city_group = df_eval.groupby("preferred_city").agg(
        count=("lead_id", "count"),
        actual_conversion_rate=("converted_binary", "mean"),
        predicted_positive_rate=("y_pred", "mean"),
        mean_proba=("y_proba", "mean")
    ).reset_index()

    # Disparate Impact Ratio relative to maximum group
    max_rate = city_group["predicted_positive_rate"].max()
    city_group["disparate_impact_ratio"] = city_group["predicted_positive_rate"] / max_rate

    # 2. By Lead Source
    source_group = df_eval.groupby("lead_source").agg(
        count=("lead_id", "count"),
        actual_conversion_rate=("converted_binary", "mean"),
        predicted_positive_rate=("y_pred", "mean"),
        mean_proba=("y_proba", "mean")
    ).reset_index()
    max_source_rate = source_group["predicted_positive_rate"].max()
    source_group["disparate_impact_ratio"] = source_group["predicted_positive_rate"] / max_source_rate

    # Plot fairness breakdown
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), dpi=300)

    # City
    sns.barplot(data=city_group, x="preferred_city", y="predicted_positive_rate",
                hue="preferred_city", palette="Blues_d", ax=axes[0], legend=False)
    axes[0].plot(city_group["preferred_city"], city_group["actual_conversion_rate"],
                 color="red", marker="o", lw=2, label="Actual Conversion Rate")
    axes[0].set_title("Model Selection Rate vs Actual Conversion by City", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("City", fontsize=11)
    axes[0].set_ylabel("Rate", fontsize=11)
    axes[0].legend(loc="upper right")
    axes[0].set_ylim([0, 0.6])

    # Lead Source
    sns.barplot(data=source_group, x="lead_source", y="predicted_positive_rate",
                hue="lead_source", palette="Greens_d", ax=axes[1], legend=False)
    axes[1].plot(source_group["lead_source"], source_group["actual_conversion_rate"],
                 color="red", marker="o", lw=2, label="Actual Conversion Rate")
    axes[1].set_title("Model Selection Rate vs Actual Conversion by Lead Source", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Lead Source", fontsize=11)
    axes[1].set_ylabel("Rate", fontsize=11)
    axes[1].legend(loc="upper right")
    axes[1].set_ylim([0, 0.6])

    plt.tight_layout()
    fig.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Fairness & Bias audit figure: {save_path}")

    # Combine for logging
    city_group["slice_type"] = "City"
    city_group = city_group.rename(columns={"preferred_city": "group"})
    source_group["slice_type"] = "Lead Source"
    source_group = source_group.rename(columns={"lead_source": "group"})
    combined_fairness = pd.concat([city_group, source_group], ignore_index=True)
    return combined_fairness
