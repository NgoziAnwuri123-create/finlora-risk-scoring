"""Feature engineering shared between the notebooks and the live app.

Mirrors notebooks/preprocessing_feature_engineering.ipynb exactly, plus
`has_invalid_amount` (present in the cleaned CSV the notebooks read from,
but not something a live scoring request supplies) computed the same way
notebooks/cleaned_data.ipynb derives it.
"""

import numpy as np
import pandas as pd

RAW_CATEGORICAL_COLUMNS = [
    "account_type", "kyc_tier", "channel", "merchant_category",
    "transaction_country", "home_country", "day_of_week",
]
RAW_NUMERIC_COLUMNS = [
    "amount", "amount_to_avg_ratio", "avg_transaction_amount_30d",
    "transaction_velocity_1h", "account_age_days", "hour_of_day",
    "personal_spend_baseline_usd", "is_cross_border", "is_new_device",
]
RAW_FEATURE_COLUMNS = RAW_CATEGORICAL_COLUMNS + RAW_NUMERIC_COLUMNS


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    hour_bins = [-1, 5, 11, 17, 23]
    hour_labels = ["Night", "Morning", "Afternoon", "Evening"]
    df["hour_bucket"] = pd.cut(df["hour_of_day"], bins=hour_bins, labels=hour_labels).astype(str)

    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"]).astype(int)
    df["amount_log"] = np.log1p(df["amount"].clip(lower=0))
    df["velocity_flag"] = (df["transaction_velocity_1h"] >= 1).astype(int)

    if "has_invalid_amount" not in df.columns:
        df["has_invalid_amount"] = (df["amount"] < 0) | (df["avg_transaction_amount_30d"] < 0)

    return df
