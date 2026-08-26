"""Model explainability: SHAP (summary/force/dependence), LIME, feature importance.

All explainers are optional dependencies — each section degrades gracefully
with install hints. Outputs land in ml/explanations/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

ML_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ML_DIR / "explanations"
sys.path.insert(0, str(ML_DIR))

from data.load_data import FEATURE_COLUMNS, load_dataset, xy_risk  # noqa: E402


def feature_importance(model, X_test) -> None:
    if not hasattr(model, "feature_importances_"):
        print("  (model has no feature_importances_ — skipping)")
        return
    importances = pd.Series(
        model.feature_importances_, index=FEATURE_COLUMNS
    ).sort_values()
    OUT_DIR.mkdir(exist_ok=True)
    importances.to_csv(OUT_DIR / "feature_importance.csv")
    print("  top features:", dict(importances.tail(3).round(3)))
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        importances.plot.barh(ax=ax, color="#0D94FB")
        ax.set_title("Feature Importance")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "feature_importance.png", dpi=120)
        plt.close(fig)
        print("  → explanations/feature_importance.png")
    except ImportError:
        print("  (matplotlib not installed — CSV only)")


def shap_analysis(model, X_test) -> None:
    try:
        import shap
    except ImportError:
        print("  SHAP not installed (pip install shap) — skipping")
        return
    OUT_DIR.mkdir(exist_ok=True)
    sample = X_test.head(200)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    try:
        import matplotlib.pyplot as plt

        plt.figure()
        shap.summary_plot(shap_values, sample, show=False)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "shap_summary.png", dpi=120)
        plt.close()

        plt.figure()
        shap.dependence_plot("amount_ratio", shap_values, sample, show=False)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "shap_dependence_amount_ratio.png", dpi=120)
        plt.close()
        print("  → shap_summary.png, shap_dependence_amount_ratio.png")
    except Exception as exc:  # noqa: BLE001
        print(f"  (plotting failed: {exc})")
    try:
        expected = (
            explainer.expected_value[1]
            if isinstance(explainer.expected_value, list)
            else explainer.expected_value
        )
        force = shap.force_plot(
            expected, shap_values[0], sample.iloc[0], matplotlib=False
        )
        shap.save_html(OUT_DIR / "shap_force_single.html", force)
        print("  → shap_force_single.html")
    except Exception as exc:  # noqa: BLE001
        print(f"  (force plot skipped: {exc})")


def lime_analysis(model, X_train, X_test) -> None:
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except ImportError:
        print("  LIME not installed (pip install lime) — skipping")
        return
    OUT_DIR.mkdir(exist_ok=True)
    explainer = LimeTabularExplainer(
        X_train.values,
        feature_names=FEATURE_COLUMNS,
        class_names=["legit", "risky"],
        mode="classification",
    )
    exp = explainer.explain_instance(
        X_test.values[0], model.predict_proba, num_features=6
    )
    (OUT_DIR / "lime_single.html").write_text(exp.as_html())
    print("  → lime_single.html")


def main() -> None:
    df = load_dataset()
    X, y = xy_risk(df)
    from sklearn.model_selection import train_test_split

    _, X_test, _, _ = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    models_dir = ML_DIR / "models"
    best = (
        (models_dir / "best.txt").read_text().strip()
        if (models_dir / "best.txt").exists()
        else "gradient_boosting"
    )
    model = joblib.load(models_dir / f"{best}.joblib")
    print(f"Explaining {best}:")

    feature_importance(model, X_test)
    if best in ("random_forest", "gradient_boosting", "decision_tree"):
        shap_analysis(model, X_test)
    else:
        print("  (SHAP TreeExplainer needs a tree model — skipping)")
    X_train, _ = X, None
    lime_analysis(model, X.head(2000), X_test)
    print(f"\nAll outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
