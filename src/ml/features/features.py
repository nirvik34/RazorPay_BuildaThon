"""Shared feature loaders for the AgentPay Guard ML models."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "dataset.csv"

FEATURE_COLUMNS = [
    "merchant_known",
    "category_allowed",
    "amount_ratio",
    "hour",
    "velocity_10m",
    "category_familiar",
    "prior_blocks_today",
    "night_hour",
    "velocity_x_amount",
    "novelty_pressure",
]


def _derive(df):
    """Windowed/interaction features that give burst context to the models."""
    df = df.copy()
    df["night_hour"] = ((df["hour"] < 8) | (df["hour"] >= 21)).astype(int)
    df["velocity_x_amount"] = (df["velocity_10m"] * df["amount_ratio"]).round(3)
    # Novelty pressure: unknown merchant AND unfamiliar category AND unusual hour
    df["novelty_pressure"] = (
        (1 - df["merchant_known"]) * (1 - df["category_familiar"]) * df["night_hour"]
    )
    return df

BLOCKED_LABELS = {"over_limit", "intent_mismatch", "splitting", "compromised"}
ANOMALY_LABELS = {"compromised", "splitting"}


def load_dataset(path: Path | str = DATASET_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run: python data/generate_dataset.py"
        )
    return pd.read_csv(path)


def xy_risk(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = _derive(df)[FEATURE_COLUMNS].copy()
    y = df["label"].isin(BLOCKED_LABELS).astype(int)
    return X, y


def xy_anomaly(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = _derive(df)[FEATURE_COLUMNS].copy()
    y = df["label"].isin(ANOMALY_LABELS).astype(int)
    return X, y
