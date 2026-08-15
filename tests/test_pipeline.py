"""
Sanity tests. Run with: pytest tests/ (from project root, after `pip install pytest`)
"""
import numpy as np
import pandas as pd

from src.features import build_feature_table, FEATURE_NAMES
from src.models import TheftDetectionEnsemble


def _toy_dataset(n_consumers=40, n_days=90, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    rows = []
    for i in range(n_consumers):
        cid = f"C{i}"
        tid = f"T{i % 4}"
        base = rng.uniform(8, 12)
        series = base + rng.normal(0, 0.5, n_days)
        label = 0
        if i % 8 == 0:  # inject obvious theft pattern
            series[n_days // 2 :] *= 0.2
            label = 1
        for d, v in zip(dates, series):
            rows.append((cid, tid, d, max(v, 0), label))
    return pd.DataFrame(rows, columns=["consumer_id", "transformer_id", "date", "consumption_kwh", "label"])


def test_feature_table_shape():
    df = _toy_dataset()
    feat = build_feature_table(df)
    assert len(feat) == 40
    for col in FEATURE_NAMES:
        assert col in feat.columns
    assert feat[FEATURE_NAMES].isna().sum().sum() == 0


def test_ensemble_trains_and_scores():
    df = _toy_dataset()
    feat = build_feature_table(df)
    ensemble = TheftDetectionEnsemble().fit(feat, feat["label"])
    scored = ensemble.score(feat)
    assert set(["risk_score", "supervised_prob", "anomaly_score"]).issubset(scored.columns)
    assert scored["risk_score"].between(0, 1).all()
    # the injected theft consumers should generally score higher than average
    theft_ids = feat.loc[feat["label"] == 1, "consumer_id"]
    theft_scores = scored.set_index("consumer_id").loc[theft_ids, "risk_score"]
    assert theft_scores.mean() > scored["risk_score"].mean()


if __name__ == "__main__":
    test_feature_table_shape()
    test_ensemble_trains_and_scores()
    print("All sanity tests passed.")
