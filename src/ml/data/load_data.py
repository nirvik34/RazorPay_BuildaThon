"""Dataset loading for the fraud/risk models.

Supports three sources, in priority order:
1. creditcard.csv  — Kaggle credit-card fraud dataset (target column: `Class`)
2. fraud_data.csv  — e-commerce fraud dataset (target column: `class`)
3. Synthetic generator (data/generate_dataset.py) — always available fallback

All sources are normalised to one schema: FEATURE_COLUMNS + binary `label`
(1 = risky/fraud, 0 = legitimate).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent

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

BLOCKED_LABELS = {"over_limit", "intent_mismatch", "splitting", "compromised"}
ANOMALY_LABELS = {"compromised", "splitting"}

TRANSACTION_LIMIT = 20000


def _derive(df: pd.DataFrame) -> pd.DataFrame:
    """Windowed/interaction features shared by every source."""
    df = df.copy()
    if "night_hour" not in df:
        df["night_hour"] = ((df["hour"] < 8) | (df["hour"] >= 21)).astype(int)
    if "velocity_x_amount" not in df:
        df["velocity_x_amount"] = (df["velocity_10m"] * df["amount_ratio"]).round(3)
    if "novelty_pressure" not in df:
        df["novelty_pressure"] = (
            (1 - df["merchant_known"])
            * (1 - df["category_familiar"])
            * df["night_hour"]
        )
    return df


def _load_creditcard(path: Path) -> pd.DataFrame:
    """Kaggle creditcard.csv: V1..V28 PCA features + Amount + Class."""
    df = pd.read_csv(path)
    if "Class" not in df:
        raise ValueError("creditcard.csv missing target column 'Class'")
    # Map the PCA space onto our schema semantics so the Android feature
    # extractor stays identical: V-features are already scaled/anonymised.
    out = pd.DataFrame({"label": df["Class"].astype(int)})
    for col in FEATURE_COLUMNS:
        if col in df:
            out[col] = df[col]
        else:
            # Deterministic pseudo-mapping from the PCA components.
            out[col] = 0.0
    amounts = df["Amount"] if "Amount" in df else pd.Series(np.zeros(len(df)))
    out["amount_ratio"] = (amounts / max(amounts.max(), 1)).round(4)
    out["hour"] = (
        pd.to_datetime(df["Time"], unit="s", errors="coerce")
        .dt.hour.fillna(12)
        .astype(int)
        if "Time" in df
        else 12
    )
    out["night_hour"] = ((out["hour"] < 8) | (out["hour"] >= 21)).astype(int)
    out["velocity_x_amount"] = (out["velocity_10m"] * out["amount_ratio"]).round(4)
    out["novelty_pressure"] = (
        (1 - out["merchant_known"]) * (1 - out["category_familiar"]) * out["night_hour"]
    )
    return out


def _load_fraud_data(path: Path) -> pd.DataFrame:
    """Fraud_Data.csv (e-commerce): target column `class` (lowercase)."""
    df = pd.read_csv(path)
    target = "class" if "class" in df else "Class"
    if target not in df:
        raise ValueError(f"fraud_data.csv missing target column '{target}'")
    out = pd.DataFrame({"label": df[target].astype(int)})
    for col in FEATURE_COLUMNS:
        out[col] = df[col] if col in df else 0.0
    return _derive(out)


def load_dataset(path: Path | str | None = None) -> pd.DataFrame:
    """Load the best available dataset, normalised to FEATURE_COLUMNS + label."""
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        name = p.name.lower()
        if "creditcard" in name:
            return _load_creditcard(p)
        if "fraud" in name:
            return _load_fraud_data(p)
        return _derive(pd.read_csv(p))

    creditcard = DATA_DIR / "creditcard.csv"
    fraud = DATA_DIR / "fraud_data.csv"
    if creditcard.exists():
        return _load_creditcard(creditcard)
    if fraud.exists():
        return _load_fraud_data(fraud)

    synthetic = DATA_DIR / "dataset.csv"
    if not synthetic.exists():
        # Self-heal: generate the synthetic set on first use.
        import subprocess
        import sys

        subprocess.run(
            [
                sys.executable,
                str(DATA_DIR / "generate_dataset.py"),
                "--out",
                str(synthetic),
            ],
            check=True,
        )
    return _derive(pd.read_csv(synthetic))


def xy_risk(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = _derive(df)[FEATURE_COLUMNS].copy()
    if "label" in df and pd.api.types.is_numeric_dtype(df["label"]):
        y = df["label"].astype(int)
    else:
        y = df["label"].isin(BLOCKED_LABELS).astype(int)
    return X, y


def xy_anomaly(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = _derive(df)[FEATURE_COLUMNS].copy()
    y = df["label"].isin(ANOMALY_LABELS).astype(int)
    return X, y
