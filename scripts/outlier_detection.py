"""
Flag statistical outliers and assign confidence scores for human review.
"""
import numpy as np
import pandas as pd


def iqr_bounds(series: pd.Series, k: float = 1.5) -> tuple[float, float]:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return float(series.min()), float(series.max())
    low = q1 - k * iqr
    high = q3 + k * iqr
    return float(low), float(high)


def z_score(x: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return (x - mean) / std


def compute_confidence(
    is_outlier: bool,
    z_abs: float,
    source_count: int,
    has_benchmark_flag: bool,
) -> float:
    """
    Confidence score 0-1 for human review priority.
    Higher = more confident this is a true outlier.
    """
    if not is_outlier:
        return 0.0
    conf = 0.0
    # Strength of statistical deviation (cap z at 4 for scaling)
    conf += min(1.0, z_abs / 4.0) * 0.4
    # Multiple sources agree (median used) -> higher confidence
    if source_count >= 2:
        conf += 0.3
    elif source_count == 1:
        conf += 0.1
    # Benchmark deviation agrees
    if has_benchmark_flag:
        conf += 0.3
    return min(1.0, conf)


def detect_outliers(merged: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Run IQR-based outlier detection on revenue and units_sold.
    Attach confidence score per outlier for human review (no auto-correction).
    """
    df = merged.copy()
    outliers = []

    for col in ["revenue", "units_sold"]:
        if col not in df.columns or df[col].dropna().empty:
            continue
        low, high = iqr_bounds(df[col].dropna())
        mean = df[col].mean()
        std = df[col].std() or 1e-6
        for idx, row in df.iterrows():
            val = row[col]
            if pd.isna(val):
                continue
            is_low = val < low
            is_high = val > high
            is_out = is_low or is_high
            z = z_score(val, mean, std)
            z_abs = abs(z)
            source_count = int(row.get("revenue_source_count", 1))
            bench_flag = bool(row.get("state_deviation_flag", False))
            confidence = compute_confidence(is_out, z_abs, source_count, bench_flag)

            if is_out:
                outliers.append({
                    "dealer_id": row["dealer_id"],
                    "metric": col,
                    "value": float(val),
                    "bound_low": low,
                    "bound_high": high,
                    "z_score": round(z, 2),
                    "confidence_score": round(confidence, 2),
                    "reason": "below_lower" if is_low else "above_upper",
                    "state_deviation_flag": bench_flag,
                })

    df["outlier_confidence_revenue"] = None
    df["outlier_confidence_units"] = None
    for o in outliers:
        did = o["dealer_id"]
        if o["metric"] == "revenue":
            df.loc[df["dealer_id"] == did, "outlier_confidence_revenue"] = o["confidence_score"]
        else:
            df.loc[df["dealer_id"] == did, "outlier_confidence_units"] = o["confidence_score"]

    return df, outliers
