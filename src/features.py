"""
Feature engineering for electricity-theft detection.

Turns a long-format daily consumption table into one feature row per
consumer. Features are grouped into four families that map directly onto
known theft signatures in the NTL (non-technical loss) literature:

  1. Distributional  - mean/std/CV/skew/kurtosis of usage
  2. Trend & drops    - sustained decreases, sudden day-over-day drops
  3. Zero/near-zero    - bypass / meter-stop signatures
  4. Periodicity       - weekly autocorrelation, weekday/weekend ratio
  5. Peer comparison    - deviation from the consumer's own transformer group
                          (theft shows up as *divergence* from neighbors who
                          share the same feeder and weather/season)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

FEATURE_NAMES = [
    "mean_kwh", "std_kwh", "cv_kwh", "skew_kwh", "kurtosis_kwh",
    "trend_slope", "max_drop_pct", "n_sudden_drops",
    "zero_day_ratio", "max_zero_streak",
    "weekly_autocorr", "weekday_weekend_ratio",
    "peer_zscore", "peer_corr", "missing_ratio",
]


def _autocorr(x: np.ndarray, lag: int) -> float:
    if len(x) <= lag or np.std(x) == 0:
        return 0.0
    x0, x1 = x[:-lag], x[lag:]
    if np.std(x0) == 0 or np.std(x1) == 0:
        return 0.0
    return float(np.corrcoef(x0, x1)[0, 1])


def _max_zero_streak(x: np.ndarray) -> int:
    streak = best = 0
    for v in x:
        if v <= 1e-6:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def featurize_consumer(series: pd.DataFrame, peer_mean_series: np.ndarray | None = None) -> dict:
    """series must have columns ['date', 'consumption_kwh'] sorted by date."""
    x = series["consumption_kwh"].to_numpy(dtype=float)
    n = len(x)
    dow = pd.to_datetime(series["date"]).dt.dayofweek.to_numpy()

    mean = float(np.mean(x))
    std = float(np.std(x))
    cv = std / mean if mean > 1e-6 else 0.0

    # trend: slope of linear fit over time, normalized by mean level
    if n > 1:
        t_centered = np.arange(n) - (n - 1) / 2.0
        denom = np.sum(t_centered ** 2)
        slope_raw = np.sum(t_centered * (x - mean)) / denom if denom > 0 else 0.0
    else:
        slope_raw = 0.0
    slope = float(slope_raw) / (mean + 1e-6)

    day_over_day = np.diff(x)
    max_drop_pct = float(np.min(day_over_day) / (mean + 1e-6)) if n > 1 else 0.0
    n_sudden_drops = int(np.sum(day_over_day < -0.5 * (mean + 1e-6)))

    zero_ratio = float(np.mean(x <= 1e-6))
    zero_streak = _max_zero_streak(x)

    weekly_ac = _autocorr(x, 7)
    weekend_mask = dow >= 5
    weekday_mean = x[~weekend_mask].mean() if (~weekend_mask).any() else mean
    weekend_mean = x[weekend_mask].mean() if weekend_mask.any() else mean
    wd_we_ratio = float(weekday_mean / (weekend_mean + 1e-6))

    if peer_mean_series is not None and len(peer_mean_series) == n:
        resid = x - peer_mean_series
        peer_zscore = float(np.mean(resid) / (np.std(peer_mean_series) + 1e-6))
        if np.std(x) > 0 and np.std(peer_mean_series) > 0:
            peer_corr = float(np.corrcoef(x, peer_mean_series)[0, 1])
        else:
            peer_corr = 0.0
    else:
        peer_zscore, peer_corr = 0.0, 0.0

    missing_ratio = float(series["consumption_kwh"].isna().mean())

    return {
        "mean_kwh": mean,
        "std_kwh": std,
        "cv_kwh": cv,
        "skew_kwh": float(np.nan_to_num(skew(x))) if (n > 2 and std > 1e-6) else 0.0,
        "kurtosis_kwh": float(np.nan_to_num(kurtosis(x))) if (n > 2 and std > 1e-6) else 0.0,
        "trend_slope": slope,
        "max_drop_pct": max_drop_pct,
        "n_sudden_drops": n_sudden_drops,
        "zero_day_ratio": zero_ratio,
        "max_zero_streak": zero_streak,
        "weekly_autocorr": weekly_ac,
        "weekday_weekend_ratio": wd_we_ratio,
        "peer_zscore": peer_zscore,
        "peer_corr": peer_corr,
        "missing_ratio": missing_ratio,
    }


def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    df: long-format ['consumer_id','transformer_id','date','consumption_kwh', optional 'label']
    Returns one row per consumer_id with FEATURE_NAMES + label (if present) + transformer_id.
    """
    df = df.sort_values(["consumer_id", "date"])

    # peer (transformer-group) mean series per date, excluding no one for simplicity/speed
    transformer_daily_mean = (
        df.groupby(["transformer_id", "date"])["consumption_kwh"].mean().reset_index()
    )

    records = []
    for cid, grp in df.groupby("consumer_id"):
        tid = grp["transformer_id"].iloc[0]
        peer = transformer_daily_mean[transformer_daily_mean["transformer_id"] == tid]
        peer = peer.sort_values("date")
        peer_series = peer["consumption_kwh"].to_numpy() if len(peer) == len(grp) else None

        feats = featurize_consumer(grp, peer_series)
        feats["consumer_id"] = cid
        feats["transformer_id"] = tid
        if "label" in grp.columns:
            feats["label"] = int(grp["label"].iloc[0])
        records.append(feats)

    cols = ["consumer_id", "transformer_id"] + FEATURE_NAMES
    out = pd.DataFrame(records)
    if "label" in out.columns:
        cols.append("label")
    return out[cols]
