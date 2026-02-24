"""
Compare dealer metrics against state-level benchmarks and apply seasonality.
"""
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
BENCH_DIR = DATA_DIR / "benchmarks"


def load_state_benchmarks() -> pd.DataFrame:
    path = BENCH_DIR / "state_trends.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_seasonality() -> pd.DataFrame:
    path = BENCH_DIR / "seasonality.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def cross_validate(merged: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Compare each dealer's revenue/units to state avg; apply seasonality index.
    Returns (merged with benchmark columns), list of deviation flags for review.
    """
    state_df = load_state_benchmarks()
    season_df = load_seasonality()
    issues = []

    if state_df.empty:
        merged["state_avg_revenue"] = None
        merged["revenue_vs_state"] = None
        merged["state_deviation_flag"] = False
    else:
        state_avg_dict = dict(zip(state_df["state"], state_df["state_avg_revenue"]))
        merged["state_avg_revenue"] = merged["state"].map(state_avg_dict)

        def _safe_ratio(rev, savg):
            if pd.isna(savg) or savg == 0:
                return None
            return float(rev) / float(savg)

        merged["revenue_vs_state"] = [
            _safe_ratio(rev, savg)
            for rev, savg in zip(merged["revenue"], merged["state_avg_revenue"])
        ]
        # Flag if outside 0.5–2.0x state avg (configurable band)
        merged["state_deviation_flag"] = merged["revenue_vs_state"].apply(
            lambda x: x is not None and (float(x) < 0.5 or float(x) > 2.0)
        )
        for _, row in merged[merged["state_deviation_flag"]].iterrows():
            issues.append({
                "dealer_id": row["dealer_id"],
                "code": "STATE_DEVIATION",
                "message": f"Revenue {row['revenue_vs_state']:.2f}x state avg (expected ~1.0)",
                "revenue_vs_state": float(row["revenue_vs_state"]) if pd.notna(row["revenue_vs_state"]) else None,
            })

    if not season_df.empty and "report_date" in merged.columns:
        merged["month"] = pd.to_datetime(merged["report_date"]).dt.month
        season_map = season_df.set_index("month")["revenue_index"]
        merged["seasonality_index"] = merged["month"].map(season_map)
        merged["revenue_season_adj"] = merged["revenue"] / merged["seasonality_index"].replace(0, 1)
    else:
        merged["seasonality_index"] = 1.0
        merged["revenue_season_adj"] = merged["revenue"]

    return merged, issues
