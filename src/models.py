"""
Two-signal ensemble for theft scoring:

  1. Supervised classifier (XGBoost) trained on confirmed theft/non-theft
     labels -> catches patterns similar to past confirmed fraud.
  2. Unsupervised anomaly detector (Isolation Forest) fit on the whole
     population -> catches novel / "zero-day" tampering patterns that don't
     resemble any labeled theft case yet, which matters because confirmed-theft
     labels in the real world are sparse and biased toward what inspectors
     already knew to look for.

Final risk score is a weighted blend, normalized to [0, 1]. Both scores are
kept alongside the blend so a reviewer can see *why* something was flagged
(e.g. high supervised prob = "looks like known theft"; high anomaly score
alone = "unusual pattern, no historical match, needs manual review").
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .features import FEATURE_NAMES

SUPERVISED_WEIGHT = 0.65
ANOMALY_WEIGHT = 0.35


class TheftDetectionEnsemble:
    def __init__(self):
        self.scaler = StandardScaler()
        self.clf = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="aucpr",
            random_state=42,
        )
        self.iso = IsolationForest(
            n_estimators=300, contamination="auto", random_state=42
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        Xs = self.scaler.fit_transform(X[FEATURE_NAMES])
        pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)
        self.clf.set_params(scale_pos_weight=pos_weight)
        self.clf.fit(Xs, y)
        self.iso.fit(Xs)
        return self

    def score(self, X: pd.DataFrame) -> pd.DataFrame:
        Xs = self.scaler.transform(X[FEATURE_NAMES])
        sup_proba = self.clf.predict_proba(Xs)[:, 1]

        # IsolationForest: lower score_samples = more anomalous. Flip + min-max normalize to [0,1].
        raw_anom = -self.iso.score_samples(Xs)
        anom_norm = (raw_anom - raw_anom.min()) / (raw_anom.max() - raw_anom.min() + 1e-9)

        blended = SUPERVISED_WEIGHT * sup_proba + ANOMALY_WEIGHT * anom_norm

        out = X[["consumer_id", "transformer_id"]].copy()
        out["supervised_prob"] = sup_proba
        out["anomaly_score"] = anom_norm
        out["risk_score"] = blended
        return out

    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "TheftDetectionEnsemble":
        return joblib.load(path)
