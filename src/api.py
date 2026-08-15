"""
FastAPI backend for electricity-theft detection.

Run (from project root):
    python -m uvicorn src.api:app --reload

Endpoints:
    GET  /health
    POST /scan
    POST /score

Train first:
    python src/train.py
"""

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException

# -------- Package-relative imports --------
from .explain import ShapExplainer
from .features import featurize_consumer, FEATURE_NAMES
from .models import TheftDetectionEnsemble
from .schemas import ReadingSeries, ScanResponse, ScanResult, ScoreResponse

# -------- Absolute paths --------
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "theft_ensemble.joblib"
FEATURE_TABLE_PATH = BASE_DIR / "models" / "feature_table.csv"

FLAG_THRESHOLD = 0.5

app = FastAPI(
    title="Electricity Theft Detection API",
    version="1.0"
)

_state = {}


@app.on_event("startup")
def load_artifacts():
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"No trained model at {MODEL_PATH}. Run `python src/train.py` first."
        )

    _state["ensemble"] = TheftDetectionEnsemble.load(str(MODEL_PATH))
    _state["explainer"] = ShapExplainer(_state["ensemble"])

    if FEATURE_TABLE_PATH.exists():
        _state["feature_table"] = pd.read_csv(FEATURE_TABLE_PATH, on_bad_lines="skip")
    else:
        _state["feature_table"] = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": "ensemble" in _state,
        "feature_table_loaded": _state.get("feature_table") is not None,
    }


@app.post("/scan", response_model=ScanResponse)
def scan(top_n: int = 25, threshold: float = FLAG_THRESHOLD):

    feat_df = _state.get("feature_table")

    if feat_df is None:
        raise HTTPException(
            status_code=404,
            detail="No stored feature table found."
        )

    ensemble = _state["ensemble"]
    explainer = _state["explainer"]

    scored = ensemble.score(feat_df)

    scored = scored.sort_values(
        by="risk_score",
        ascending=False
    )

    top = scored.head(top_n)

    top_feats = (
        feat_df
        .set_index("consumer_id")
        .loc[top["consumer_id"]]
        .reset_index()
    )

    reasons = explainer.top_reasons(top_feats, k=3)

    results = []

    for (_, row), reason in zip(top.iterrows(), reasons):

        results.append(
            ScanResult(
                consumer_id=row["consumer_id"],
                transformer_id=row["transformer_id"],
                risk_score=round(float(row["risk_score"]), 4),
                supervised_prob=round(float(row["supervised_prob"]), 4),
                anomaly_score=round(float(row["anomaly_score"]), 4),
                reasons=reason,
            )
        )

    return ScanResponse(
        total_consumers=len(scored),
        flagged_count=int(
            (scored["risk_score"] >= threshold).sum()
        ),
        threshold=threshold,
        results=results,
    )


@app.post("/score", response_model=ScoreResponse)
def score(
    series: ReadingSeries,
    threshold: float = FLAG_THRESHOLD
):

    if len(series.dates) != len(series.consumption_kwh):
        raise HTTPException(
            status_code=400,
            detail="dates and consumption_kwh lengths differ."
        )

    if len(series.dates) < 14:
        raise HTTPException(
            status_code=400,
            detail="Need at least 14 days of readings."
        )

    df = pd.DataFrame({
        "date": series.dates,
        "consumption_kwh": series.consumption_kwh,
    })

    feats = featurize_consumer(
        df,
        peer_mean_series=None
    )

    feats["consumer_id"] = series.consumer_id
    feats["transformer_id"] = "UNKNOWN"

    feat_row = pd.DataFrame([feats])[
        ["consumer_id", "transformer_id"] + FEATURE_NAMES
    ]

    ensemble = _state["ensemble"]

    scored = ensemble.score(feat_row).iloc[0]

    reasons = _state["explainer"].top_reasons(
        feat_row,
        k=3
    )[0]

    return ScoreResponse(
        consumer_id=series.consumer_id,
        risk_score=round(float(scored["risk_score"]), 4),
        supervised_prob=round(float(scored["supervised_prob"]), 4),
        anomaly_score=round(float(scored["anomaly_score"]), 4),
        flagged=bool(scored["risk_score"] >= threshold),
        reasons=reasons,
        note="Peer comparison unavailable in ad-hoc mode."
    )