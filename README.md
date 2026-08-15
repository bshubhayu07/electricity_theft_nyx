# Electricity Theft Detection

Flags suspicious consumer accounts from smart-meter consumption data.
Python-only backend: FastAPI serving a two-signal ML ensemble
(XGBoost + Isolation Forest) with SHAP-based explanations for every flag.

## Why this approach (not just "train XGBoost on labels")

Most tutorials train one classifier on confirmed theft labels and stop there.
Two problems with that in the real world:

1. **Confirmed-theft labels are sparse and biased** — they only cover the
   patterns inspectors already knew to look for. A purely supervised model
   inherits that blind spot.
2. **Utilities need reasons, not just scores** — flagging an account for a
   manual inspection without justification wastes inspector time and erodes
   trust in the system.

So this pipeline combines:

| Signal | Model | Catches |
|---|---|---|
| Supervised | XGBoost (class-weighted) | Patterns similar to past confirmed theft |
| Unsupervised | Isolation Forest | Novel/"zero-day" tampering with no historical match |
| Explainability | SHAP (TreeExplainer) | Human-readable reasons per flagged account |
| Peer comparison | Transformer-group z-score/correlation | Divergence from neighbors on the same feeder, controlling for weather/season |

Final `risk_score = 0.65 * supervised_prob + 0.35 * anomaly_score`, both
components reported separately — an account with high anomaly score but low
supervised probability is "unusual pattern, no historical match, needs human
review" rather than a confident theft call.

## Architecture

```
data/smart_meter_readings.csv   (long format: consumer_id, transformer_id, date, consumption_kwh, [label])
        │
        ▼
src/features.py     → one feature row per consumer (15 features, see below)
        │
        ▼
src/models.py        → TheftDetectionEnsemble (XGBoost + IsolationForest)
        │
        ▼
src/explain.py       → SHAP reasons per account
        │
        ▼
src/api.py (FastAPI) → POST /scan   (batch, ranks whole population)
                        POST /score  (single consumer, ad-hoc raw series)
```

## Features engineered (per consumer)

- **Distributional**: mean, std, coefficient of variation, skew, kurtosis
- **Trend & drops**: normalized trend slope, largest single-day drop %, count of sudden drops
- **Zero/near-zero**: share of zero-consumption days, longest zero streak (classic meter-bypass signature)
- **Periodicity**: weekly autocorrelation, weekday/weekend ratio (theft often flattens or disrupts normal weekly rhythm)
- **Peer comparison**: z-score and correlation vs. the daily mean of consumers on the same transformer (theft shows up as *divergence from neighbors*, not just low usage — a neighbor's usage also dropping means it's probably just cold weather, not theft)
- **Data quality**: missing-reading ratio (tampering sometimes causes meter communication gaps)

## Quickstart

```bash
pip install -r requirements.txt

# 1. Train (auto-generates a synthetic dataset the first time you run it)
python -m src.train

# 2. Serve
python -m uvicorn src.api:app --reload --port 8000
```

Then:

```bash
# Ranked list of most suspicious accounts
curl -X POST "http://127.0.0.1:8000/scan?top_n=10"

# Score one consumer from raw readings (no stored data needed)
curl -X POST http://127.0.0.1:8000/score -H "Content-Type: application/json" -d '{
  "consumer_id": "C_ADHOC_1",
  "dates": ["2024-01-01", "2024-01-02", "...at least 14 days..."],
  "consumption_kwh": [10.2, 9.8, "..."]
}'
```

## Dashboard

With the API running, start the Streamlit dashboard from the project root:

```bash
streamlit run dashboard.py
```

The dashboard calls `http://127.0.0.1:8000/scan?top_n=...` by default. To use
a remote API, set `THEFT_API_URL` to the API base URL before starting Streamlit.

## Using real data instead of the synthetic generator

Point `DATA_PATH` in `src/train.py` at your own CSV with the same long-format
columns (`consumer_id, transformer_id, date, consumption_kwh, label`).
`label` (1 = confirmed theft, 0 = normal) is only needed for training the
supervised half — the Isolation Forest half works unsupervised, so you can
still get anomaly scores even for consumers with no confirmed history.

**Recommended public benchmark**: the **SGCC (State Grid Corporation of
China)** dataset — the standard benchmark in the theft-detection literature.
<cite index="1-1">It contains 42,372 consumer records, with 3,615 flagged as abnormal (theft) and 38,757 normal.</cite>
It's mirrored on Kaggle (search "SGCC electricity theft detection") and via
the original GitHub release from the Zheng et al. 2018 IEEE TII paper *"Wide
and Deep Convolutional Neural Networks for Electricity-Theft Detection."*
Reshape it to the long format above (`pandas.melt` on the date columns) and
it drops straight into `build_feature_table`.

Two other datasets worth knowing about if you want to extend this:
- **PRECON** (Pakistan Residential Electricity Consumption) — used alongside SGCC in several recent ensemble+XAI papers.
- **Irish CER Smart Metering Project** — higher-frequency (30-min) residential data, good if you want to add time-of-day/tamper-signature features later.

## Honest caveats (say these out loud in a hackathon Q&A)

- The bundled synthetic generator produces *cleanly separable* theft patterns
  (that's why the demo hits ~1.0 ROC-AUC) — real theft is messier and will
  score lower. Swap in SGCC or real utility data before quoting accuracy numbers.
- Peer-group comparison assumes consumers are correctly mapped to a shared
  transformer/feeder — bad topology data will pollute that feature.
- Isolation Forest catches *statistical* outliers, not all of which are theft
  (e.g., a vacant/relocated household). Treat unsupervised-only flags as
  "needs review," not "confirmed theft."
- This is a decision-support tool, not a legal determination — final action
  on any flagged account should go through human inspection.

## Extending further

- Swap XGBoost for LightGBM/CatBoost if you want faster training on bigger data — same `sklearn`-style API.
- Add an LSTM/1D-CNN autoencoder on raw daily sequences as a third signal if you have GPU time (catches temporal shape anomalies the hand-crafted features miss).
- Add SMOTE (`imbalanced-learn`) if your real theft ratio is under ~2% and `scale_pos_weight` alone isn't enough.
- Persist `/scan` results to SQLite with a timestamp so you can show *trend of risk score over successive scans* for an account — a rising risk score over time is itself a strong signal.
