"""
End-to-end training entrypoint.

    python src/train.py

Loads data/smart_meter_readings.csv (generating a synthetic set first if it
doesn't exist), builds features, trains the ensemble, evaluates on a held-out
split, and saves model artifacts to models/.
"""

import os

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from .features import build_feature_table, FEATURE_NAMES
from .models import TheftDetectionEnsemble
from .explain import ShapExplainer

DATA_PATH = "data/smart_meter_readings.csv"
MODEL_PATH = "models/theft_ensemble.joblib"


def main():
    if not os.path.exists(DATA_PATH):
        from generate_data import generate
        generate(out_path=DATA_PATH)

    print("Loading readings...")
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])

    print("Engineering features (one row per consumer)...")
    feat_df = build_feature_table(df)
    print(f"  -> {len(feat_df)} consumers, {len(FEATURE_NAMES)} features")

    train_df, test_df = train_test_split(
        feat_df, test_size=0.25, stratify=feat_df["label"], random_state=42
    )

    ensemble = TheftDetectionEnsemble()
    ensemble.fit(train_df, train_df["label"])

    scored = ensemble.score(test_df)
    scored["label"] = test_df["label"].to_numpy()

    print("\n=== Held-out evaluation ===")
    print(f"ROC-AUC (supervised):  {roc_auc_score(scored['label'], scored['supervised_prob']):.3f}")
    print(f"ROC-AUC (blended risk): {roc_auc_score(scored['label'], scored['risk_score']):.3f}")
    print(f"PR-AUC  (blended risk): {average_precision_score(scored['label'], scored['risk_score']):.3f}")
    print()
    preds = (scored["risk_score"] >= 0.5).astype(int)
    print(classification_report(scored["label"], preds, target_names=["normal", "theft"]))

    os.makedirs("models", exist_ok=True)
    ensemble.save(MODEL_PATH)
    feat_df.to_csv("models/feature_table.csv", index=False)
    print(f"Saved model -> {MODEL_PATH}")

    print("\n=== Top 5 highest-risk accounts (held-out set) with reasons ===")
    explainer = ShapExplainer(ensemble)
    top5 = scored.sort_values("risk_score", ascending=False).head(5)
    top5_feats = test_df.set_index("consumer_id").loc[top5["consumer_id"]].reset_index()
    reasons = explainer.top_reasons(top5_feats, k=3)
    for (_, row), r in zip(top5.iterrows(), reasons):
        print(f"  {row['consumer_id']}  risk={row['risk_score']:.3f}  "
              f"(sup={row['supervised_prob']:.2f}, anom={row['anomaly_score']:.2f})  "
              f"actual_label={row['label']}")
        for reason in r:
            print(f"     - {reason}")


if __name__ == "__main__":
    main()
