"""Time alignment and correlation for client and server telemetry."""

from __future__ import annotations

import pandas as pd


def _frame(points: list[dict], label: str) -> pd.DataFrame:
    rows = []
    for point in points:
        timestamp = point.get("timestamp")
        if timestamp is None:
            continue
        value = point.get("value")
        if value is None:
            continue
        rows.append({"timestamp": pd.to_datetime(timestamp, utc=True),
                     label: float(value), "metric": point.get("metric", label)})
    if not rows:
        return pd.DataFrame(columns=["timestamp", label])
    frame = pd.DataFrame(rows)
    return frame.groupby("timestamp", as_index=False)[label].mean().sort_values("timestamp")


def correlate_series(
    load_points: list[dict],
    server_points: list[dict],
    bucket_seconds: int = 60,
    min_observations: int = 5,
) -> dict:
    """Resample two independently sampled sources to common UTC buckets."""
    if bucket_seconds < 1:
        raise ValueError("bucket_seconds must be at least 1")
    left = _frame(load_points, "load_value")
    right = _frame(server_points, "server_value")
    if left.empty or right.empty:
        return {"available": False, "reason": "Both data sources need timestamped numeric values.",
                "observations": 0, "correlation": None, "buckets": []}

    left = left.set_index("timestamp").resample(f"{bucket_seconds}s").mean()
    right = right.set_index("timestamp").resample(f"{bucket_seconds}s").mean()
    joined = left.join(right, how="inner").dropna()
    if len(joined) < min_observations:
        return {"available": False,
                "reason": f"At least {min_observations} aligned observations are required.",
                "observations": len(joined), "correlation": None,
                "buckets": joined.reset_index().to_dict(orient="records")}
    corr = joined["load_value"].corr(joined["server_value"])
    return {
        "available": corr is not None and pd.notna(corr),
        "method": "Pearson correlation on aligned UTC bucket means",
        "bucket_seconds": bucket_seconds,
        "observations": len(joined),
        "correlation": float(corr) if pd.notna(corr) else None,
        "interpretation": "Correlation indicates co-movement, not causation.",
        "buckets": joined.reset_index().to_dict(orient="records"),
    }


def correlate_metric_pairs(load_points: list[dict], server_points: list[dict],
                           bucket_seconds: int = 60) -> list[dict]:
    load_metrics = sorted({p.get("metric") for p in load_points if p.get("metric")})
    server_metrics = sorted({p.get("metric") for p in server_points if p.get("metric")})
    results = []
    for left_metric in load_metrics:
        lp = [p for p in load_points if p.get("metric") == left_metric]
        for right_metric in server_metrics:
            rp = [p for p in server_points if p.get("metric") == right_metric]
            result = correlate_series(lp, rp, bucket_seconds)
            results.append({"load_metric": left_metric, "server_metric": right_metric, **result})
    return results
