"""
Explainability layer. Uses SHAP TreeExplainer on the supervised XGBoost model
so every flag comes with human-readable reasons an auditor/inspector can act
on, instead of a bare probability.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from .features import FEATURE_NAMES

READABLE = {
    "mean_kwh": "average daily usage",
    "std_kwh": "usage volatility",
    "cv_kwh": "relative volatility (CV)",
    "skew_kwh": "usage skew",
    "kurtosis_kwh": "usage spikiness",
    "trend_slope": "usage trend over time",
    "max_drop_pct": "largest single-day drop",
    "n_sudden_drops": "number of sudden drops",
    "zero_day_ratio": "share of zero-consumption days",
    "max_zero_streak": "longest zero-consumption streak",
    "weekly_autocorr": "weekly pattern consistency",
    "weekday_weekend_ratio": "weekday/weekend usage ratio",
    "peer_zscore": "deviation from neighbors on same transformer",
    "peer_corr": "correlation with neighbors on same transformer",
    "missing_ratio": "share of missing meter readings",
}


class ShapExplainer:
    def __init__(self, ensemble):
        self.ensemble = ensemble
        self.explainer = shap.TreeExplainer(ensemble.clf)

    def top_reasons(self, X: pd.DataFrame, k: int = 3) -> list[list[str]]:
        Xs = self.ensemble.scaler.transform(X[FEATURE_NAMES])
        shap_values = self.explainer.shap_values(Xs)
        reasons = []
        for i in range(Xs.shape[0]):
            row_shap = shap_values[i]
            order = np.argsort(-np.abs(row_shap))[:k]
            row_reasons = []
            for idx in order:
                feat = FEATURE_NAMES[idx]
                direction = "elevated" if row_shap[idx] > 0 else "lowered"
                row_reasons.append(
                    f"{READABLE.get(feat, feat)} {direction} risk "
                    f"(value={X.iloc[i][feat]:.3f})"
                )
            reasons.append(row_reasons)
        return reasons
