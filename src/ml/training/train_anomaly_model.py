"""Train the behaviour anomaly model (Isolation Forest on legitimate baseline)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.features import load_dataset, xy_anomaly  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contamination", type=float, default=0.05)
    args = parser.parse_args()

    df = load_dataset()
    X, y = xy_anomaly(df)

    baseline = X[y == 0]
    model = IsolationForest(contamination=args.contamination, random_state=args.seed)
    model.fit(baseline)

    predictions = (model.predict(X) == -1).astype(int)
    report = classification_report(y, predictions, output_dict=True, zero_division=0)

    out_dir = Path(__file__).parent.parent / "models"
    out_dir.mkdir(exist_ok=True)
    joblib.dump(model, out_dir / "anomaly_model.joblib")
    (out_dir / "anomaly_metrics.json").write_text(json.dumps(report, indent=2))

    print("Anomaly model saved to models/anomaly_model.joblib")
    print(
        f"precision(1)={report['1']['precision']:.3f} recall(1)={report['1']['recall']:.3f}"
    )


if __name__ == "__main__":
    main()
