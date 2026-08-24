"""Train the transaction risk model (GradientBoosting stand-in for XGBoost)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.features import load_dataset, xy_risk  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = load_dataset()
    X, y = xy_risk(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=args.seed, stratify=y
    )

    model = GradientBoostingClassifier(random_state=args.seed)
    model.fit(X_train, y_train)

    report = classification_report(y_test, model.predict(X_test), output_dict=True)
    out_dir = Path(__file__).parent.parent / "models"
    out_dir.mkdir(exist_ok=True)
    joblib.dump(model, out_dir / "risk_model.joblib")
    (out_dir / "risk_metrics.json").write_text(json.dumps(report, indent=2))

    print("Risk model saved to models/risk_model.joblib")
    print(
        f"precision(1)={report['1']['precision']:.3f} recall(1)={report['1']['recall']:.3f} f1={report['1']['f1-score']:.3f}"
    )


if __name__ == "__main__":
    main()
