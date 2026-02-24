"""
Merge records from multiple sources by dealer_id using median.
Flags large discrepancies between sources for review.
"""
import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def merge_sources(loaded: list[tuple[str, pd.DataFrame]]) -> tuple[pd.DataFrame, list[dict]]:
    """
    Merge all source DataFrames by dealer_id.
    For numeric fields use median across sources; record std and source count for confidence.
    Returns (merged_df, conflict_flags for human review).
    """
    if not loaded:
        return pd.DataFrame(), []

    all_dfs = []
    for name, df in loaded:
        d = df.copy()
        d["_source"] = name
        all_dfs.append(d)

    combined = pd.concat(all_dfs, ignore_index=True)

    g = combined.groupby("dealer_id", as_index=True)
    # Build merged from one aggregation to get consistent index/order, then add columns
    merged = g["revenue"].median().reset_index()
    merged.columns = ["dealer_id", "revenue"]
    merged["dealer_name"] = g["dealer_name"].first().values
    merged["state"] = g["state"].first().values
    merged["revenue_std"] = g["revenue"].std().fillna(0).values
    merged["revenue_source_count"] = g["revenue"].count().values.astype(int)
    merged["units_sold"] = g["units_sold"].median().values
    merged["units_sold_std"] = g["units_sold"].std().fillna(0).values
    merged["report_date"] = g["report_date"].max().values

    # Flag conflicts: high relative std across sources -> human review
    conflict_flags = []
    for _, row in merged.iterrows():
        if row["revenue_source_count"] < 2:
            continue
        cv_rev = (row["revenue_std"] / row["revenue"]) * 100 if row["revenue"] else 0
        if cv_rev > 10:
            conflict_flags.append({
                "dealer_id": row["dealer_id"],
                "code": "REVENUE_DISCREPANCY",
                "message": f"Revenue varies across sources (cv={cv_rev:.1f}%)",
                "revenue_median": float(row["revenue"]),
                "revenue_std": float(row["revenue_std"]),
                "source_count": int(row["revenue_source_count"]),
            })
    return merged, conflict_flags
