"""
Synthetic smart-meter dataset generator.

Mimics the structure of the widely-used SGCC (State Grid Corporation of China)
electricity-theft benchmark: daily kWh consumption per consumer over a long
window, consumers grouped under shared transformers/feeders (so peer
comparison is meaningful), and a minority of consumers exhibiting real-world
theft signatures.

Use this to develop/demo the pipeline. Swap in real smart-meter data by
producing a long-format CSV with the same columns (see README).
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

THEFT_PATTERNS = ["sudden_drop", "progressive_drop", "periodic_zero", "erratic_tamper"]


def _seasonal_base(n_days: int, level: float) -> np.ndarray:
    """Smooth seasonal + weekly base load shared by a transformer group."""
    t = np.arange(n_days)
    yearly = 0.25 * np.sin(2 * np.pi * t / 365.0)
    weekly = 0.08 * np.sin(2 * np.pi * t / 7.0)
    return level * (1 + yearly + weekly)


def _inject_theft(series: np.ndarray, pattern: str, start_idx: int) -> np.ndarray:
    s = series.copy()
    n = len(s)
    if pattern == "sudden_drop":
        s[start_idx:] *= RNG.uniform(0.15, 0.35)
    elif pattern == "progressive_drop":
        ramp = np.linspace(1.0, RNG.uniform(0.2, 0.4), n - start_idx)
        s[start_idx:] *= ramp
    elif pattern == "periodic_zero":
        mask_days = RNG.choice(
            np.arange(start_idx, n), size=int((n - start_idx) * 0.35), replace=False
        )
        s[mask_days] = 0.0
    elif pattern == "erratic_tamper":
        noise = RNG.uniform(0.1, 1.3, size=n - start_idx)
        s[start_idx:] = s[start_idx:] * noise
    return np.clip(s, 0, None)


def generate(
    n_consumers: int = 600,
    n_days: int = 365,
    n_transformers: int = 25,
    theft_ratio: float = 0.085,
    out_path: str = "data/smart_meter_readings.csv",
) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    consumer_ids = [f"C{100000+i}" for i in range(n_consumers)]
    transformer_of = {cid: f"T{RNG.integers(0, n_transformers):03d}" for cid in consumer_ids}

    # shared base load per transformer group (peer signal)
    transformer_level = {
        f"T{i:03d}": RNG.uniform(8, 20) for i in range(n_transformers)
    }
    transformer_base = {
        tid: _seasonal_base(n_days, lvl) for tid, lvl in transformer_level.items()
    }

    n_theft = int(n_consumers * theft_ratio)
    theft_ids = set(RNG.choice(consumer_ids, size=n_theft, replace=False))

    rows = []
    for cid in consumer_ids:
        tid = transformer_of[cid]
        indiv_scale = RNG.uniform(0.6, 1.5)
        noise = RNG.normal(0, 0.6, size=n_days)
        series = transformer_base[tid] * indiv_scale + noise
        series = np.clip(series, 0.1, None)

        label = 0
        pattern = None
        if cid in theft_ids:
            label = 1
            pattern = RNG.choice(THEFT_PATTERNS)
            start_idx = RNG.integers(int(n_days * 0.3), int(n_days * 0.75))
            series = _inject_theft(series, pattern, start_idx)

        for d, kwh in zip(dates, series):
            rows.append((cid, tid, d, round(float(kwh), 3), label))

    df = pd.DataFrame(
        rows, columns=["consumer_id", "transformer_id", "date", "consumption_kwh", "label"]
    )
    df.to_csv(out_path, index=False)
    print(f"Generated {len(consumer_ids)} consumers x {n_days} days -> {out_path}")
    print(f"Theft consumers: {n_theft} ({theft_ratio:.1%})")
    return df


if __name__ == "__main__":
    generate()
