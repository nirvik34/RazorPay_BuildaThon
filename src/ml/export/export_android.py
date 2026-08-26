"""Export the best trained model as a lightweight bundle for on-device
Android inference — pure JSON, no ML runtime dependency on the phone.

Bundle format (assets/ml/risk_model.json):
{
  "model_type": "logistic_regression" | "mlp" | "tree_ensemble",
  "features": [...ordered feature names...],
  "scaler": {"mean": [...], "scale": [...]},          # standardise inputs
  "weights": [...], "bias": 0.0,                       # logistic regression
  "layers": [{"weights": [[..]], "biases": [..]}],     # mlp
  "trees": [{"feature": i, "threshold": t, "left": node, "right": node, "value": v}],
  "learning_rate": 0.1,                                # gradient boosting
  "threshold": 0.5,
  "metrics": {...}
}
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

ML_DIR = Path(__file__).resolve().parent.parent
ANDROID_ASSETS = ML_DIR.parent / "android" / "app" / "src" / "main" / "assets" / "ml"


def tree_to_dict(tree, feature_names) -> dict:
    return _node(tree.tree_, 0, feature_names)


def _node(tree, node_id: int, feature_names) -> dict:
    if tree.children_left[node_id] == -1:  # leaf
        value = tree.value[node_id][0]
        return {"value": float(value[1] / max(value.sum(), 1))}
    return {
        "feature": feature_names[int(tree.feature[node_id])],
        "threshold": round(float(tree.threshold[node_id]), 6),
        "left": _node(tree, tree.children_left[node_id], feature_names),
        "right": _node(tree, tree.children_right[node_id], feature_names),
    }


def export_model(model, scaler, model_name: str, metrics: dict) -> dict:
    feature_names = (
        list(scaler.feature_names_in_) if hasattr(scaler, "feature_names_in_") else None
    )
    bundle: dict = {
        "model_type": model_name,
        "features": feature_names,
        "scaler": {
            "mean": np.round(scaler.mean_, 6).tolist(),
            "scale": np.round(scaler.scale_, 6).tolist(),
        },
        "threshold": 0.5,
        "metrics": metrics,
    }

    if model_name == "logistic_regression":
        bundle["weights"] = np.round(model.coef_[0], 6).tolist()
        bundle["bias"] = round(float(model.intercept_[0]), 6)
    elif model_name == "mlp":
        bundle["layers"] = [
            {
                "weights": np.round(coef, 6).tolist(),
                "biases": np.round(bias, 6).tolist(),
            }
            for coef, bias in zip(model.coefs_, model.intercepts_)
        ]
    elif model_name in ("random_forest", "gradient_boosting"):
        estimators = model.estimators_
        bundle["model_type"] = "tree_ensemble"
        bundle["trees"] = [tree_to_dict(est, feature_names) for est in estimators]
        if model_name == "gradient_boosting":
            bundle["learning_rate"] = float(model.learning_rate_)
            bundle["base_score"] = float(model.init_.constant_[0][0])
    else:
        raise ValueError(f"No Android export path for model type: {model_name}")
    return bundle


def main() -> None:
    models_dir = ML_DIR / "models"
    best = (
        (models_dir / "best.txt").read_text().strip()
        if (models_dir / "best.txt").exists()
        else "gradient_boosting"
    )
    scaler = joblib.load(models_dir / "scaler.joblib")
    model = joblib.load(models_dir / f"{best}.joblib")
    comparison = (
        json.loads((models_dir / "comparison.json").read_text())
        if (models_dir / "comparison.json").exists()
        else {}
    )

    bundle = export_model(model, scaler, best, comparison.get(best, {}))
    bundle["exportedAt"] = str(Path(models_dir).stat().st_mtime)

    ANDROID_ASSETS.mkdir(parents=True, exist_ok=True)
    out = ANDROID_ASSETS / "risk_model.json"
    out.write_text(json.dumps(bundle, separators=(",", ":")))

    size_kb = out.stat().st_size / 1024
    print(f"Exported {best} → {out} ({size_kb:.1f} KB)")
    if size_kb > 512:
        print(
            "  ⚠ bundle > 512 KB — consider logistic_regression or a smaller forest for mobile"
        )


if __name__ == "__main__":
    main()
