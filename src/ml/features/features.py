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
]

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
    X = df[FEATURE_COLUMNS].copy()
    y = df["label"].isin(BLOCKED_LABELS).astype(int)
    return X, y


def xy_anomaly(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURE_COLUMNS].copy()
    y = df["label"].isin(ANOMALY_LABELS).astype(int)
    return X, y
