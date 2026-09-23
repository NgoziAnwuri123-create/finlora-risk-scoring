"""Model performance detail, feature importance, and live-traffic monitoring."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib.logging_store import clear_predictions, read_predictions
from lib.model import artifacts_ready, load_metadata
from lib.palette import BLUE, RED, STATUS_CRITICAL, STATUS_GOOD, STATUS_WARNING, plotly_layout_defaults

st.set_page_config(page_title="Finlora | Observability", page_icon="🔍", layout="wide")
st.title("🔍 Fraud Model Observability")

if not artifacts_ready():
    st.error("No deployment artifacts found. Run `notebooks/final_evaluation.ipynb` first.")
    st.stop()

meta = load_metadata()
test_metrics = meta["test_metrics"]
threshold = meta["operating_threshold"]

tab_perf, tab_features, tab_live, tab_quality = st.tabs(
    ["Test-set performance", "Feature importance (SHAP)", "Live traffic monitoring", "Data quality & drift"]
)

# ---------------------------------------------------------------- performance
with tab_perf:
    st.subheader("Model card")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Served model", "HistGradientBoosting")
    c2.metric("Test rows", f"{test_metrics['n_test']:,}")
    c3.metric("Test fraud rate", f"{test_metrics['test_fraud_rate']:.3%}")
    c4.metric("Operating threshold", f"{threshold:.3f}")

    st.caption(
        "Metrics below come from `notebooks/final_evaluation.ipynb`'s single, one-time look at the "
        "held-out test set — not the validation set the model was tuned against."
    )

    c5, c6 = st.columns(2)
    c5.metric("Test ROC-AUC", f"{test_metrics['roc_auc']:.4f}")
    c6.metric("Test PR-AUC", f"{test_metrics['pr_auc']:.4f}")

    st.subheader("ROC and Precision-Recall curves (test set)")
    col_roc, col_pr = st.columns(2)
    with col_roc:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=test_metrics["roc_curve"]["fpr"], y=test_metrics["roc_curve"]["tpr"],
                                  mode="lines", name="Test ROC", line=dict(color=BLUE, width=3)))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance",
                                  line=dict(dash="dash", color="#c3c2b7")))
        fig.update_layout(title="ROC curve", xaxis_title="False positive rate", yaxis_title="True positive rate",
                           **plotly_layout_defaults())
        st.plotly_chart(fig, width="stretch")
    with col_pr:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=test_metrics["pr_curve"]["recall"], y=test_metrics["pr_curve"]["precision"],
                                  mode="lines", name="Test PR", line=dict(color=RED, width=3)))
        fig.update_layout(title="Precision-Recall curve", xaxis_title="Recall", yaxis_title="Precision",
                           **plotly_layout_defaults())
        st.plotly_chart(fig, width="stretch")

    st.subheader(f"Confusion matrix @ operating threshold ({threshold:.3f})")
    cm = np.array(test_metrics["confusion_matrix"])
    fig = px.imshow(cm, text_auto=True, x=test_metrics["confusion_matrix_labels"],
                     y=test_metrics["confusion_matrix_labels"], color_continuous_scale="Blues",
                     labels=dict(x="Predicted", y="Actual"), title="Test-set confusion matrix")
    fig.update_layout(**plotly_layout_defaults())
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------ feature importance
with tab_features:
    st.subheader("Top 15 features by mean |SHAP value|")
    st.caption(
        "SHAP (SHapley Additive exPlanations) attributes each prediction to its input features — "
        "see `notebooks/shap_explainability.ipynb` for the full global/local breakdown, including "
        "why this ranking differs from the raw EDA correlation ranking."
    )
    shap_top = pd.Series(meta["shap_top_features"]).sort_values(ascending=True)
    fig = px.bar(shap_top, orientation="h", labels={"index": "feature", "value": "mean |SHAP value|"},
                 color_discrete_sequence=[BLUE])
    fig.update_layout(showlegend=False, height=500, **plotly_layout_defaults())
    st.plotly_chart(fig, width="stretch")

    shap_img = Path(__file__).resolve().parent.parent.parent / "eda" / "shap_beeswarm.png"
    if shap_img.exists():
        st.image(str(shap_img), caption="SHAP beeswarm: direction and magnitude of each feature's effect")

# ------------------------------------------------------------------- live traffic
with tab_live:
    st.subheader("Traffic scored through this app")
    logs = read_predictions()

    if logs.empty:
        st.info(
            "No predictions logged yet. Score a transaction or a batch CSV on the Home page — "
            "every prediction is logged here for monitoring."
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total predictions logged", f"{len(logs):,}")
        c2.metric("Flagged for review", f"{(logs['decision'] == 'Flag / review').mean():.2%}")
        c3.metric("Mean fraud score", f"{logs['score'].mean():.3%}")
        c4.metric("High risk tier share", f"{(logs['risk_tier'] == 'High').mean():.2%}")

        logs["logged_at"] = pd.to_datetime(logs["logged_at"])
        logs_by_period = logs.set_index("logged_at").resample("1min").size().rename("count").reset_index()
        fig = px.line(logs_by_period, x="logged_at", y="count", title="Requests over time (1-min buckets)",
                       color_discrete_sequence=[BLUE])
        fig.update_layout(**plotly_layout_defaults())
        st.plotly_chart(fig, width="stretch")

        col_a, col_b = st.columns(2)
        with col_a:
            baseline_sample = pd.Series(test_metrics["test_proba_sample"])
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=baseline_sample, name="Test set (baseline)", histnorm="probability density",
                                        opacity=0.6, marker_color=BLUE))
            fig.add_trace(go.Histogram(x=logs["score"], name="Live traffic", histnorm="probability density",
                                        opacity=0.6, marker_color=RED))
            fig.update_layout(barmode="overlay", title="Fraud score distribution: baseline vs. live",
                               xaxis_title="Fraud probability", **plotly_layout_defaults())
            st.plotly_chart(fig, width="stretch")
        with col_b:
            decision_counts = logs["decision"].value_counts().reset_index()
            decision_counts.columns = ["decision", "count"]
            fig = px.pie(decision_counts, names="decision", values="count", title="Decision mix (live traffic)",
                         color="decision", color_discrete_map={"Approve": STATUS_GOOD, "Flag / review": STATUS_CRITICAL})
            fig.update_layout(**plotly_layout_defaults())
            st.plotly_chart(fig, width="stretch")

        st.subheader("Recent predictions")
        st.dataframe(logs.sort_values("logged_at", ascending=False).head(100), width="stretch")

        if st.button("Clear prediction log", type="secondary"):
            clear_predictions()
            st.rerun()

# --------------------------------------------------------------- data quality & drift
with tab_quality:
    st.subheader("Feature drift: live traffic vs. training baseline")
    st.caption(
        "Population Stability Index (PSI) compares each numeric feature's live distribution "
        "against the distribution it was trained on. PSI < 0.1 = stable, 0.1-0.25 = moderate "
        "shift worth watching, > 0.25 = significant drift."
    )
    logs = read_predictions()

    if logs.empty:
        st.info("No live traffic yet — drift metrics need logged predictions from the Home page.")
    else:
        def psi(baseline_quantile_edges, live_values, n_bins=10):
            edges = np.unique(baseline_quantile_edges)
            if len(edges) < 3:
                return 0.0
            live_counts, _ = np.histogram(live_values, bins=edges)
            live_pct = np.clip(live_counts / max(len(live_values), 1), 1e-4, None)
            expected_pct = np.full(len(edges) - 1, 1.0 / (len(edges) - 1))
            return float(np.sum((live_pct - expected_pct) * np.log(live_pct / expected_pct)))

        rows = []
        for feat, stats in meta["feature_baseline"]["numeric"].items():
            if feat not in logs.columns:
                continue
            edges = np.array(stats["quantiles"])
            edges = np.linspace(edges[0], edges[-1], 11) if len(set(edges)) < 3 else edges
            score = psi(edges, logs[feat].dropna().values)
            rows.append({"feature": feat, "psi": round(score, 4),
                         "status": "🔴 Drift" if score > 0.25 else ("🟡 Watch" if score > 0.1 else "🟢 Stable")})
        drift_df = pd.DataFrame(rows).sort_values("psi", ascending=False)
        st.dataframe(drift_df, width="stretch", hide_index=True)

        st.subheader("Categorical value coverage")
        st.caption("Categories seen in live traffic that were never seen during training (handled via one-hot 'unknown', but worth reviewing).")
        unseen_any = False
        for feat, known_vals in meta["categorical_values"].items():
            if feat not in logs.columns:
                continue
            live_vals = set(logs[feat].dropna().unique().tolist())
            unseen = live_vals - set(known_vals)
            if unseen:
                unseen_any = True
                st.warning(f"**{feat}**: unseen values in live traffic — {sorted(unseen)}")
        if not unseen_any:
            st.success("No unseen categorical values in live traffic.")

        st.subheader("Missing values in scored input")
        missing = logs[meta["raw_feature_columns"]].isna().sum()
        missing = missing[missing > 0]
        if missing.empty:
            st.success("No missing values in logged prediction inputs.")
        else:
            st.dataframe(missing.rename("missing_count"), width="stretch")
