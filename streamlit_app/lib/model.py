"""Shared helpers for loading the fraud model and scoring transactions.

Loads the final artifacts from notebooks/final_evaluation.ipynb: the fitted
preprocessor + HistGradientBoostingClassifier chosen in
notebooks/model_optimization_precision_recall.ipynb, and the consolidated
deployment_metadata.json (threshold, categorical dropdown values, drift
baseline, test metrics, and the model-selection journey) it produced.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from .features import engineer_features

ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = ROOT / "artifacts"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
PREDICTIONS_LOG = LOGS_DIR / "predictions.csv"

MODEL_PATH = ARTIFACTS_DIR / "precision_recall_balanced_model.joblib"
PREPROCESSOR_PATH = ARTIFACTS_DIR / "preprocessor.joblib"
METADATA_PATH = ARTIFACTS_DIR / "deployment_metadata.json"


def artifacts_ready() -> bool:
    return MODEL_PATH.exists() and PREPROCESSOR_PATH.exists() and METADATA_PATH.exists()


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_resource
def load_preprocessor():
    return joblib.load(PREPROCESSOR_PATH)


@st.cache_data
def load_metadata() -> dict:
    with open(METADATA_PATH) as f:
        return json.load(f)


def score_dataframe(raw_df: pd.DataFrame, feature_columns: list[str]):
    """Raw scoring-request columns -> engineered features -> fraud probability.

    `raw_df` must contain RAW_FEATURE_COLUMNS (the fields the Home page form
    and the batch-CSV template collect); everything downstream of that
    (hour_bucket, is_weekend, amount_log, velocity_flag, has_invalid_amount,
    one-hot encoding, scaling) is handled here so every caller scores
    identically.
    """
    model = load_model()
    preprocessor = load_preprocessor()
    engineered = engineer_features(raw_df)
    X = engineered[feature_columns]
    X_processed = preprocessor.transform(X)
    return model.predict_proba(X_processed)[:, 1]


def risk_tier(score: float, threshold: float) -> str:
    if score >= threshold:
        return "High"
    if score >= threshold * 0.5:
        return "Medium"
    return "Low"
