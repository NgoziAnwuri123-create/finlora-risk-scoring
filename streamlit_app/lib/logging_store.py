"""Append-only log of scored transactions, read back by the observability page.

Kept as a flat CSV rather than a database: this is a single-node demo
deployment, and a CSV is trivial to inspect, back up, or swap out for a
real store (a table, a metrics backend) later without changing the
scoring or observability code much.
"""

from pathlib import Path

import pandas as pd

from .model import PREDICTIONS_LOG

LOG_COLUMNS = [
    "logged_at", "source", "score", "decision", "risk_tier",
    "account_type", "kyc_tier", "channel", "merchant_category",
    "transaction_country", "home_country", "day_of_week",
    "amount", "amount_to_avg_ratio", "avg_transaction_amount_30d",
    "transaction_velocity_1h", "account_age_days", "hour_of_day",
    "personal_spend_baseline_usd", "is_cross_border", "is_new_device",
]


def log_predictions(rows: pd.DataFrame) -> None:
    rows = rows.reindex(columns=LOG_COLUMNS)
    write_header = not PREDICTIONS_LOG.exists()
    rows.to_csv(PREDICTIONS_LOG, mode="a", header=write_header, index=False)


def read_predictions() -> pd.DataFrame:
    if not PREDICTIONS_LOG.exists():
        return pd.DataFrame(columns=LOG_COLUMNS)
    df = pd.read_csv(PREDICTIONS_LOG, parse_dates=["logged_at"])
    return df


def clear_predictions() -> None:
    if PREDICTIONS_LOG.exists():
        Path(PREDICTIONS_LOG).unlink()
