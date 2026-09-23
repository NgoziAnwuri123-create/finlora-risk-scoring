"""Executive dashboard: the model-selection journey, final performance, and why."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib.logging_store import read_predictions
from lib.model import artifacts_ready, load_metadata
from lib.palette import (
    BLUE, RED, STAGE_COLORS, STATUS_CRITICAL, STATUS_GOOD, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY, plotly_layout_defaults,
)

st.set_page_config(page_title="Finlora | Dashboard", page_icon="📊", layout="wide")

if not artifacts_ready():
    st.error("No deployment artifacts found. Run `notebooks/final_evaluation.ipynb` first.")
    st.stop()

meta = load_metadata()
test_metrics = meta["test_metrics"]
op_point = meta["operating_point"]
threshold = meta["operating_threshold"]
journey = pd.DataFrame(meta["model_journey"])

st.markdown(
    """
    <style>
    .flr-tile {
        background: #fcfcfb; border: 1px solid #e1e0d9; border-radius: 10px;
        padding: 1rem 1.1rem; height: 100%;
    }
    .flr-tile-label { font-size: 0.8rem; color: #52514e; font-weight: 500; margin-bottom: 0.3rem; }
    .flr-tile-value { font-size: 1.9rem; font-weight: 700; color: #0b0b0b; font-variant-numeric: tabular-nums; }
    .flr-tile-sub { font-size: 0.78rem; color: #898781; margin-top: 0.15rem; }
    .flr-callout {
        background: #fcfcfb; border-left: 4px solid #2a78d6; border-radius: 6px;
        padding: 1rem 1.2rem; font-size: 0.92rem; color: #0b0b0b; line-height: 1.55;
    }
    .flr-callout b { color: #0b0b0b; }
    </style>
    """,
    unsafe_allow_html=True,
)


def stat_tile(label: str, value: str, sub: str = "", accent: str = TEXT_PRIMARY):
    st.markdown(
        f"""<div class="flr-tile">
              <div class="flr-tile-label">{label}</div>
              <div class="flr-tile-value" style="color:{accent};">{value}</div>
              <div class="flr-tile-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


st.title("📊 Finlora Fraud Model — Dashboard")
st.caption(
    "How the deployed model performs, how it got here across four rounds of optimization, "
    "and why it lands where it does. All test-set numbers are from a single, one-time evaluation "
    "in `notebooks/final_evaluation.ipynb`."
)

# ---------------------------------------------------------------- hero KPI row
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    stat_tile("Test PR-AUC", f"{test_metrics['pr_auc']:.3f}", "precision-recall ranking quality")
with k2:
    stat_tile("Test ROC-AUC", f"{test_metrics['roc_auc']:.3f}", "overall separability")
with k3:
    stat_tile("Precision @ threshold", f"{test_metrics['confusion_matrix'][1][1] / (test_metrics['confusion_matrix'][1][1] + test_metrics['confusion_matrix'][0][1]):.1%}",
              "of flagged transactions are truly fraud", accent=BLUE)
with k4:
    stat_tile("Recall @ threshold", f"{test_metrics['confusion_matrix'][1][1] / (test_metrics['confusion_matrix'][1][1] + test_metrics['confusion_matrix'][1][0]):.1%}",
              "of actual fraud caught", accent=RED)
with k5:
    stat_tile("Base fraud rate", f"{test_metrics['test_fraud_rate']:.2%}", "why accuracy alone is meaningless here")

st.write("")

# ------------------------------------------------------- journey + SHAP row
col_journey, col_shap = st.columns([3, 2])

with col_journey:
    st.subheader("The optimization journey, in precision-recall space")
    st.caption(
        "Every stage is one deliberate objective: match a recall floor, then improve F1, then favor "
        "recall (F2), then balance both — each point is that stage's actual (recall, precision)."
    )

    fig = go.Figure()

    # Final test-set PR curve as the achievable-frontier backdrop
    fig.add_trace(go.Scatter(
        x=test_metrics["pr_curve"]["recall"], y=test_metrics["pr_curve"]["precision"],
        mode="lines", name="Test PR curve (final model)", line=dict(color="#c3c2b7", width=2),
        hoverinfo="skip",
    ))

    # 70%/70% target zone
    fig.add_shape(type="line", x0=0.70, x1=0.70, y0=0, y1=1, line=dict(color=TEXT_MUTED, width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=1, y0=0.70, y1=0.70, line=dict(color=TEXT_MUTED, width=1, dash="dot"))
    fig.add_annotation(x=0.70, y=1.0, text="70% target", showarrow=False, yshift=10,
                        font=dict(size=11, color=TEXT_MUTED))

    # Journey stages, connected in order, each with its own fixed identity color
    fig.add_trace(go.Scatter(
        x=journey["recall"], y=journey["precision"], mode="lines", line=dict(color="#d8d7d0", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))
    for _, row in journey.iterrows():
        short_stage = row["stage"].split(". ", 1)[1] if ". " in row["stage"] else row["stage"]
        fig.add_trace(go.Scatter(
            x=[row["recall"]], y=[row["precision"]], mode="markers", name=short_stage,
            marker=dict(size=15, color=STAGE_COLORS.get(row["stage"], BLUE), line=dict(width=2, color="white")),
            hovertemplate=f"<b>{short_stage}</b><br>Recall: {row['recall']:.1%}<br>"
                          f"Precision: {row['precision']:.1%}<br>F1: {row['f1']:.3f}<extra></extra>",
        ))

    journey_layout = plotly_layout_defaults()
    journey_layout["legend"] = dict(orientation="h", yanchor="bottom", y=-0.35, font=dict(size=11))
    fig.update_layout(
        xaxis_title="Recall", yaxis_title="Precision", xaxis_range=[0, 1.02], yaxis_range=[0, 1.02],
        height=460, **journey_layout,
    )
    st.plotly_chart(fig, width="stretch")

with col_shap:
    st.subheader("What the model actually relies on")
    st.caption("Top features by mean |SHAP value| (full breakdown in `notebooks/shap_explainability.ipynb`).")
    shap_top = pd.Series(meta["shap_top_features"]).sort_values(ascending=True).tail(8)
    fig = px.bar(shap_top, orientation="h", color_discrete_sequence=[BLUE])
    fig.update_layout(showlegend=False, height=460, xaxis_title="mean |SHAP value|", yaxis_title="",
                       **plotly_layout_defaults())
    st.plotly_chart(fig, width="stretch")

st.write("")

# --------------------------------------------------------------- narrative + confusion matrix
col_narrative, col_cm = st.columns([3, 2])

with col_narrative:
    st.subheader("Why 70% precision and 70% recall together isn't reachable")
    st.markdown(
        f"""<div class="flr-callout">
        <b>Checked empirically</b> in <code>notebooks/model_optimization_precision_recall.ipynb</code>
        across six models — three baseline candidates, a stronger algorithm, one with extra engineered
        features, and a PR-AUC-tuned final version — <b>no threshold on any of them cleared both 70% marks
        at once</b> on validation. The closest achievable balance point was <b>{op_point['precision']:.1%}
        precision / {op_point['recall']:.1%} recall</b>.
        <br><br>
        <b>Why:</b> the EDA found most numeric features (transaction amount, account age, personal spend
        baseline) heavily <i>overlap</i> between fraud and legitimate transactions — only
        <code>transaction_velocity_1h</code> cleanly separates the classes. A classifier can only be as
        precise at a given recall as its features let it distinguish the classes; closing this gap further
        would most likely need new signal (device fingerprinting, network reputation) rather than more
        tuning on what's already here.
        <br><br>
        <b>On the untouched test set</b>, the deployed model actually landed at
        <b>{test_metrics['confusion_matrix'][1][1] / (test_metrics['confusion_matrix'][1][1] + test_metrics['confusion_matrix'][0][1]):.1%} precision</b>
        — within normal sampling variance of the validation-based ceiling, not evidence it was wrong.
        </div>""",
        unsafe_allow_html=True,
    )

    st.write("")
    st.dataframe(
        journey.rename(columns={"stage": "Stage", "model": "Model", "recall": "Recall",
                                 "precision": "Precision", "f1": "F1"})
        .style.format({"Recall": "{:.1%}", "Precision": "{:.1%}", "F1": "{:.3f}"}),
        width="stretch", hide_index=True,
    )

with col_cm:
    st.subheader("Test-set confusion matrix")
    cm = np.array(test_metrics["confusion_matrix"])
    fig = px.imshow(cm, text_auto=True, x=test_metrics["confusion_matrix_labels"],
                     y=test_metrics["confusion_matrix_labels"], color_continuous_scale="Blues",
                     labels=dict(x="Predicted", y="Actual"))
    fig.update_layout(height=380, coloraxis_showscale=False, **plotly_layout_defaults())
    st.plotly_chart(fig, width="stretch")
    st.caption(f"At threshold {threshold:.3f} — {int(cm[1][1])} fraud caught, {int(cm[1][0])} missed, "
               f"{int(cm[0][1])} legitimate transactions flagged for review.")

# --------------------------------------------------------------------- live snapshot
logs = read_predictions()
if not logs.empty:
    st.write("")
    st.subheader("Live traffic snapshot")
    l1, l2, l3 = st.columns([1, 1, 2])
    with l1:
        stat_tile("Predictions logged", f"{len(logs):,}")
    with l2:
        stat_tile("Flagged for review", f"{(logs['decision'] == 'Flag / review').mean():.1%}", accent=STATUS_CRITICAL)
    with l3:
        decision_counts = logs["decision"].value_counts().reset_index()
        decision_counts.columns = ["decision", "count"]
        fig = px.bar(decision_counts, x="count", y="decision", orientation="h",
                     color="decision", color_discrete_map={"Approve": STATUS_GOOD, "Flag / review": STATUS_CRITICAL})
        fig.update_layout(height=140, showlegend=False, xaxis_title="", yaxis_title="",
                           margin=dict(t=10, l=10, r=10, b=10), template="plotly_white",
                           font=dict(size=12, color=TEXT_SECONDARY))
        st.plotly_chart(fig, width="stretch")
    st.caption("Full drift and monitoring detail on the Observability page.")
    st.page_link("pages/2_Observability.py", label="🔍 Go to Observability", icon="🔍")
else:
    st.info("No live traffic yet — score a transaction on the Home page to populate this section.")
