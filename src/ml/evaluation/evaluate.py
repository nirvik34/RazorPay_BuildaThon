"""Evaluate trained models + dedicated circumvention detector tests."""

from __future__ import annotations

import json
from pathlib import Path

import joblib

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.features import FEATURE_COLUMNS, load_dataset, xy_risk  # noqa: E402

TRANSACTION_LIMIT = 20000


def detect_circumvention(amounts: list[int], window_seconds: int = 300) -> dict:
    prior = [a for a in amounts[:-1] if abs(a - amounts[-1]) / max(a, 1) <= 0.15]
    aggregate = sum(prior) + amounts[-1]
    if len(prior) >= 2 and aggregate >= 0.9 * TRANSACTION_LIMIT:
        score = min(100, 55 + 15 * len(prior))
        return {"detected": True, "score": score, "aggregate": aggregate}
    return {
        "detected": False,
        "score": min(60, len(prior) * 20),
        "aggregate": aggregate,
    }


def circumvention_tests() -> list[tuple[str, bool]]:
    naive = [9800, 9700, 9900]
    third = detect_circumvention(naive)
    first = detect_circumvention(naive[:1])
    second = detect_circumvention([9800, 9700])
    normal = detect_circumvention([500, 480, 520])
    return [
        ("3x ~9.8K same session detected", third["detected"]),
        ("aggregate equals 29400", third["aggregate"] == 29400),
        ("circumvention score >= 80 on third", third["score"] >= 80),
        ("single item not flagged", not first["detected"]),
        ("two items below threshold not flagged", not second["detected"]),
        ("normal small purchases not flagged", not normal["detected"]),
    ]


def main() -> None:
    models_dir = Path(__file__).parent.parent / "models"
    results: dict = {}

    risk_path = models_dir / "risk_model.joblib"
    if risk_path.exists():
        model = joblib.load(risk_path)
        df = load_dataset()
        X, y = xy_risk(df)
        report = json.loads((models_dir / "risk_metrics.json").read_text())
        results["risk_model"] = {
            "accuracy": report.get("accuracy"),
            "precision_blocked": report.get("1", {}).get("precision"),
            "recall_blocked": report.get("1", {}).get("recall"),
            "features": FEATURE_COLUMNS,
        }

    anomaly_path = models_dir / "anomaly_model.joblib"
    if anomaly_path.exists():
        results["anomaly_model"] = json.loads(
            (models_dir / "anomaly_metrics.json").read_text()
        )

    checks = circumvention_tests()
    results["circumvention_tests"] = {name: ok for name, ok in checks}
    results["circumvention_all_passed"] = all(ok for _, ok in checks)

    print(json.dumps(results, indent=2))

    out = Path(__file__).parent / "metrics.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved evaluation to {out}")

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit(f"Circumvention tests FAILED: {failed}")
    print("All circumvention detector tests passed.")


if __name__ == "__main__":
    main()
