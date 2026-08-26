"""Train the full model zoo and track everything in MLflow.

Models: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting,
MLP — plus CNN / RNN / LSTM when TensorFlow is installed (optional).

Every run is logged to MLflow when available, with a zero-dependency JSON
fallback tracker (ml/runs/*.json) so experiments are never lost.

The best model by F1 is exported to the Android app as a lightweight JSON
bundle (see export/export_android.py).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.load_data import FEATURE_COLUMNS, load_dataset, xy_risk  # noqa: E402

ML_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ML_DIR / "models"
RUNS_DIR = ML_DIR / "runs"

# ---------------------------------------------------------------- tracking
try:
    import mlflow

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


class Tracker:
    """MLflow when installed, JSON-file fallback otherwise."""

    def __init__(self) -> None:
        self.runs: list[dict] = []
        if MLFLOW_AVAILABLE:
            mlflow.set_experiment("agentpay-risk")

    def log(
        self,
        model_name: str,
        params: dict,
        metrics: dict,
        artifact_path: str | None = None,
    ) -> None:
        entry = {
            "model": model_name,
            "params": params,
            "metrics": metrics,
            "ts": time.time(),
        }
        self.runs.append(entry)
        if MLFLOW_AVAILABLE:
            with mlflow.start_run(run_name=model_name):
                mlflow.log_params(params)
                mlflow.log_metrics(metrics)
                if artifact_path and Path(artifact_path).exists():
                    mlflow.log_artifact(artifact_path)

    def save(self) -> None:
        RUNS_DIR.mkdir(exist_ok=True)
        (RUNS_DIR / "runs.json").write_text(json.dumps(self.runs, indent=2))


def evaluate(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    proba = (
        model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else pred
    )
    return {
        "f1": round(f1_score(y_test, pred, zero_division=0), 4),
        "precision": round(precision_score(y_test, pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4)
        if len(set(y_test)) > 1
        else 0.0,
    }


# ---------------------------------------------------------------- keras (optional)
def train_keras_family(X_train, y_train, X_test, y_test, tracker: Tracker) -> dict:
    """CNN / RNN / LSTM via Keras. Skipped cleanly when TF is not installed."""
    try:
        import tensorflow as tf
    except ImportError:
        print(
            "TensorFlow not installed — skipping CNN/RNN/LSTM (pip install tensorflow)"
        )
        return {}

    results: dict = {}
    n_features = X_train.shape[1]

    def make(name: str) -> tf.keras.Model:
        model = tf.keras.Sequential(name=name)
        if name == "cnn":
            model.add(
                tf.keras.layers.Reshape((n_features, 1), input_shape=(n_features,))
            )
            model.add(tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same"))
            model.add(tf.keras.layers.MaxPooling1D(2))
            model.add(tf.keras.layers.Flatten())
        elif name in ("rnn", "lstm"):
            model.add(
                tf.keras.layers.Reshape((n_features, 1), input_shape=(n_features,))
            )
            layer = (
                tf.keras.layers.LSTM(32)
                if name == "lstm"
                else tf.keras.layers.SimpleRNN(32)
            )
            model.add(layer)
        else:
            raise ValueError(name)
        model.add(tf.keras.layers.Dense(16, activation="relu"))
        model.add(tf.keras.layers.Dense(1, activation="sigmoid"))
        model.compile(
            optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"]
        )
        return model

    for name in ("cnn", "rnn", "lstm"):
        model = make(name)
        model.fit(
            X_train.values.astype("float32"),
            y_train.values.astype("float32"),
            epochs=12,
            batch_size=256,
            verbose=0,
            validation_split=0.1,
        )
        pred = (
            (model.predict(X_test.values.astype("float32"), verbose=0) > 0.5)
            .astype(int)
            .ravel()
        )
        metrics = {
            "f1": round(f1_score(y_test, pred, zero_division=0), 4),
            "precision": round(precision_score(y_test, pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, pred, zero_division=0), 4),
        }
        tracker.log(name, {"epochs": 12, "framework": "keras"}, metrics)
        results[name] = {"model": model, "metrics": metrics}
        print(f"  {name:10} f1={metrics['f1']}")
    return results


# ---------------------------------------------------------------- main
def main() -> None:
    seed = 42
    df = load_dataset()
    X, y = xy_risk(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )

    scaler = StandardScaler().fit(X_train)
    X_train_s = pd.DataFrame(scaler.transform(X_train), columns=FEATURE_COLUMNS)
    X_test_s = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLUMNS)

    tracker = Tracker()
    candidates = {
        "logistic_regression": (
            LogisticRegression(max_iter=1000, random_state=seed),
            X_train_s,
            X_test_s,
        ),
        "decision_tree": (
            DecisionTreeClassifier(max_depth=8, random_state=seed),
            X_train,
            X_test,
        ),
        "random_forest": (
            RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=-1),
            X_train,
            X_test,
        ),
        "gradient_boosting": (
            GradientBoostingClassifier(random_state=seed),
            X_train,
            X_test,
        ),
        "mlp": (
            MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=400, random_state=seed),
            X_train_s,
            X_test_s,
        ),
    }

    MODELS_DIR.mkdir(exist_ok=True)
    results: dict[str, dict] = {}
    print(f"Training on {len(X_train):,} rows · {len(FEATURE_COLUMNS)} features\n")

    for name, (model, xtr, xte) in candidates.items():
        t0 = time.time()
        model.fit(xtr, y_train)
        metrics = evaluate(model, xte, y_test)
        metrics["train_seconds"] = round(time.time() - t0, 2)
        results[name] = {"model": model, "scaled": xtr is X_train_s, "metrics": metrics}
        tracker.log(name, {"seed": seed}, metrics)
        joblib.dump(model, MODELS_DIR / f"{name}.joblib")
        print(f"  {name:20} f1={metrics['f1']}  auc={metrics['roc_auc']}")

    keras_results = train_keras_family(X_train_s, y_train, X_test_s, y_test, tracker)
    for name, res in keras_results.items():
        results[name] = {
            "model": res["model"],
            "scaled": True,
            "metrics": res["metrics"],
            "keras": True,
        }

    tracker.save()
    best = max(results, key=lambda n: results[n]["metrics"]["f1"])
    print(f"\nBest model: {best} (f1={results[best]['metrics']['f1']})")

    (ML_DIR / "models" / "comparison.json").write_text(
        json.dumps(
            {n: r["metrics"] for n, r in results.items()},
            indent=2,
        )
    )
    joblib.dump(scaler, MODELS_DIR / "scaler.joblib")
    (MODELS_DIR / "best.txt").write_text(best)
    print(f"Saved comparison.json, scaler, best={best}")
    print("Next: python export/export_android.py  → bundles it for the Android app")


if __name__ == "__main__":
    main()
