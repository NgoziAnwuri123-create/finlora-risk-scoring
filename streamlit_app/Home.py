"""Finlora fraud risk-scoring app: single-transaction and batch scoring."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent))
from lib.features import RAW_FEATURE_COLUMNS
from lib.logging_store import log_predictions
from lib.model import artifacts_ready, load_metadata, risk_tier, score_dataframe
from lib.palette import RISK_TIER_COLORS

st.set_page_config(page_title="Finlora | Fraud Risk Scoring", page_icon="🛡️", layout="wide")

st.title("🛡️ Finlora Fraud Risk Scoring")

if not artifacts_ready():
    st.error(
        "No deployment artifacts found in `artifacts/`. Run "
        "`notebooks/final_evaluation.ipynb` from the project root first, then reload this page."
    )
    st.stop()

meta = load_metadata()
threshold = meta["operating_threshold"]
op_point = meta["operating_point"]
cat_values = meta["categorical_values"]
feature_columns = meta["feature_columns"]

st.caption(
    f"Score transactions for fraud probability using Finlora's {meta['served_model']} risk model — "
    f"operating point: **{op_point['precision']:.0%} precision / {op_point['recall']:.0%} recall** on validation."
)

tab_single, tab_batch = st.tabs(["Score a transaction", "Batch scoring (CSV)"])

with tab_single:
    st.subheader("Transaction details")
    col1, col2, col3 = st.columns(3)

    with col1:
        account_type = st.selectbox("Account type", cat_values["account_type"])
        kyc_tier = st.selectbox("KYC tier", cat_values["kyc_tier"])
        channel = st.selectbox("Channel", cat_values["channel"])
        merchant_category = st.selectbox("Merchant category", cat_values["merchant_category"])

    with col2:
        transaction_country = st.selectbox("Transaction country", cat_values["transaction_country"])
        home_country = st.selectbox("Home country", cat_values["home_country"])
        day_of_week = st.selectbox("Day of week", cat_values["day_of_week"])
        hour_of_day = st.slider("Hour of day", 0, 23, 12)

    with col3:
        amount = st.number_input("Amount", min_value=0.0, value=10000.0, step=100.0)
        amount_to_avg_ratio = st.number_input("Amount to 30d avg ratio", min_value=0.0, value=1.0, step=0.1)
        avg_transaction_amount_30d = st.number_input("Avg transaction amount (30d)", min_value=0.0, value=9000.0, step=100.0)
        transaction_velocity_1h = st.number_input("Transactions in last 1h", min_value=0, value=0, step=1)

    col4, col5, col6 = st.columns(3)
    with col4:
        account_age_days = st.number_input("Account age (days)", min_value=0, value=500, step=1)
    with col5:
        personal_spend_baseline_usd = st.number_input("Personal spend baseline (USD)", min_value=0.0, value=100.0, step=10.0)
    with col6:
        is_cross_border = st.checkbox("Cross-border transaction")
        is_new_device = st.checkbox("New / unrecognized device")

    if st.button("Score transaction", type="primary"):
        row = pd.DataFrame([{
            "account_type": account_type, "kyc_tier": kyc_tier, "channel": channel,
            "merchant_category": merchant_category, "transaction_country": transaction_country,
            "home_country": home_country, "day_of_week": day_of_week,
            "amount": amount, "amount_to_avg_ratio": amount_to_avg_ratio,
            "avg_transaction_amount_30d": avg_transaction_amount_30d,
            "transaction_velocity_1h": transaction_velocity_1h,
            "account_age_days": account_age_days, "hour_of_day": hour_of_day,
            "personal_spend_baseline_usd": personal_spend_baseline_usd,
            "is_cross_border": int(is_cross_border), "is_new_device": int(is_new_device),
        }])

        score = float(score_dataframe(row, feature_columns)[0])
        tier = risk_tier(score, threshold)
        decision = "Flag / review" if score >= threshold else "Approve"

        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Fraud probability", f"{score:.2%}")
        m2.markdown(
            f"<div style='font-size:0.875rem;color:#52514e;margin-bottom:0.2rem;'>Risk tier</div>"
            f"<div style='font-size:1.75rem;font-weight:600;color:{RISK_TIER_COLORS[tier]};'>{tier}</div>",
            unsafe_allow_html=True,
        )
        m3.metric("Decision", decision, delta=f"threshold {threshold:.2%}", delta_color="off")
        st.progress(min(score, 1.0))

        log_row = row.copy()
        log_row.insert(0, "logged_at", datetime.now(timezone.utc).isoformat())
        log_row.insert(1, "source", "single")
        log_row.insert(2, "score", score)
        log_row.insert(3, "decision", decision)
        log_row.insert(4, "risk_tier", tier)
        log_predictions(log_row)
        st.caption("Logged to `logs/predictions.csv` — visible on the Observability page.")

with tab_batch:
    st.subheader("Score a CSV of transactions")
    st.caption("Upload a CSV with columns: " + ", ".join(RAW_FEATURE_COLUMNS))
    uploaded = st.file_uploader("Transactions CSV", type="csv")

    if uploaded is not None:
        batch_df = pd.read_csv(uploaded)
        missing_cols = [c for c in RAW_FEATURE_COLUMNS if c not in batch_df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {missing_cols}")
        else:
            X = batch_df[RAW_FEATURE_COLUMNS].copy()
            scores = score_dataframe(X, feature_columns)
            batch_df["fraud_score"] = scores
            batch_df["risk_tier"] = [risk_tier(s, threshold) for s in scores]
            batch_df["decision"] = ["Flag / review" if s >= threshold else "Approve" for s in scores]

            st.success(f"Scored {len(batch_df):,} transactions. "
                       f"{(batch_df['decision'] == 'Flag / review').sum():,} flagged for review.")
            st.dataframe(batch_df.head(200), width="stretch")
            st.download_button(
                "Download scored CSV",
                batch_df.to_csv(index=False).encode("utf-8"),
                file_name="scored_transactions.csv",
                mime="text/csv",
            )

            log_rows = X.copy()
            log_rows.insert(0, "logged_at", datetime.now(timezone.utc).isoformat())
            log_rows.insert(1, "source", "batch")
            log_rows.insert(2, "score", scores)
            log_rows.insert(3, "decision", batch_df["decision"].values)
            log_rows.insert(4, "risk_tier", batch_df["risk_tier"].values)
            log_predictions(log_rows)
            st.caption(f"Logged {len(log_rows):,} rows to `logs/predictions.csv`.")

st.sidebar.header("Model")
st.sidebar.write(f"**Served model:** {meta['served_model']}")
st.sidebar.write(f"**Operating threshold:** {threshold:.2%}")
st.sidebar.write(f"**Validation:** {op_point['precision']:.1%} precision / {op_point['recall']:.1%} recall")
st.sidebar.write(f"**Test set (final check):** {meta['test_metrics']['pr_auc']:.3f} PR-AUC")
st.sidebar.page_link("pages/1_Dashboard.py", label="📊 Go to Dashboard", icon="📊")
st.sidebar.page_link("pages/2_Observability.py", label="🔍 Go to Observability", icon="🔍")
