"""
Dealer data processing script: ETL + business rules.
Run directly or via cron/scheduler. Outputs JSON for dashboard/API.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

# Add project root for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import (
    DATA_DIR,
    OUTPUT_DIR,
    DEALERS_CSV,
    RESULTS_JSON,
    MIN_HEALTHY_MARGIN_PCT,
    LOW_MARGIN_WARNING_PCT,
    NEGATIVE_MARGIN_CRITICAL,
    SLOW_TURNOVER_DAYS,
    CRITICAL_TURNOVER_DAYS,
    INACTIVE_DAYS_THRESHOLD,
    MIN_ORDER_COUNT_LOW_ACTIVITY,
)


def load_dealer_data() -> pd.DataFrame:
    """Load dealer data from CSV or Excel."""
    data_path = PROJECT_ROOT / DATA_DIR / DEALERS_CSV
    if not data_path.exists():
        # Try Excel
        xlsx = PROJECT_ROOT / DATA_DIR / DEALERS_CSV.replace(".csv", ".xlsx")
        if xlsx.exists():
            return pd.read_excel(xlsx)
        raise FileNotFoundError(f"No data file found in {PROJECT_ROOT / DATA_DIR}")
    return pd.read_csv(data_path)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date columns if present."""
    if "last_order_date" in df.columns:
        df["last_order_date"] = pd.to_datetime(df["last_order_date"], errors="coerce")
    return df


def apply_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Apply business rules and return enriched dataframe + list of issues/flaws.
    """
    issues = []
    df = df.copy()
    df["issues"] = ""
    df["issue_count"] = 0

    for idx, row in df.iterrows():
        row_issues = []

        # Rule 1: Profit margin
        margin = row.get("margin_pct")
        if pd.notna(margin):
            if NEGATIVE_MARGIN_CRITICAL and margin < 0:
                row_issues.append({
                    "code": "NEGATIVE_MARGIN",
                    "severity": "critical",
                    "message": f"Negative profit margin: {margin:.1f}%",
                })
            elif margin < LOW_MARGIN_WARNING_PCT:
                row_issues.append({
                    "code": "LOW_MARGIN",
                    "severity": "warning",
                    "message": f"Low margin ({margin:.1f}%) below {LOW_MARGIN_WARNING_PCT}%",
                })
            elif margin < MIN_HEALTHY_MARGIN_PCT:
                row_issues.append({
                    "code": "BELOW_TARGET_MARGIN",
                    "severity": "info",
                    "message": f"Margin {margin:.1f}% below target {MIN_HEALTHY_MARGIN_PCT}%",
                })

        # Rule 2: Stock turnover
        turnover = row.get("stock_turnover_days")
        if pd.notna(turnover):
            if turnover >= CRITICAL_TURNOVER_DAYS:
                row_issues.append({
                    "code": "CRITICAL_SLOW_TURNOVER",
                    "severity": "critical",
                    "message": f"Very slow stock turnover: {int(turnover)} days",
                })
            elif turnover >= SLOW_TURNOVER_DAYS:
                row_issues.append({
                    "code": "SLOW_TURNOVER",
                    "severity": "warning",
                    "message": f"Slow stock turnover: {int(turnover)} days",
                })

        # Rule 3: Inactivity
        last_order = row.get("last_order_date")
        if pd.notna(last_order):
            try:
                days_since = (pd.Timestamp.now() - pd.Timestamp(last_order)).days
                if days_since > INACTIVE_DAYS_THRESHOLD:
                    row_issues.append({
                        "code": "INACTIVE_DEALER",
                        "severity": "warning",
                        "message": f"No order for {days_since} days",
                    })
            except Exception:
                pass

        # Rule 4: Low order count
        orders = row.get("order_count")
        if pd.notna(orders) and orders < MIN_ORDER_COUNT_LOW_ACTIVITY:
            row_issues.append({
                "code": "LOW_ACTIVITY",
                "severity": "info",
                "message": f"Low order count: {int(orders)}",
            })

        # Rule 5: Status-based
        status = str(row.get("status", "")).lower()
        if status == "inactive":
            row_issues.append({
                "code": "STATUS_INACTIVE",
                "severity": "warning",
                "message": "Dealer marked inactive",
            })

        df.at[idx, "issues"] = json.dumps(row_issues)
        df.at[idx, "issue_count"] = len(row_issues)
        issues.extend([{"dealer_id": row.get("dealer_id"), **i} for i in row_issues])

    return df, issues


def compute_summary(df: pd.DataFrame, issues: list[dict]) -> dict:
    """Compute KPIs and summary for dashboard."""
    total_revenue = df["revenue"].sum() if "revenue" in df.columns else 0
    total_cost = df["cost"].sum() if "cost" in df.columns else 0
    profit = total_revenue - total_cost
    avg_margin = df["margin_pct"].mean() if "margin_pct" in df.columns else 0

    by_severity = {}
    for i in issues:
        s = i.get("severity", "info")
        by_severity[s] = by_severity.get(s, 0) + 1

    return {
        "total_dealers": len(df),
        "total_revenue": round(float(total_revenue), 2),
        "total_cost": round(float(total_cost), 2),
        "total_profit": round(float(profit), 2),
        "avg_margin_pct": round(float(avg_margin), 2),
        "issues_count": len(issues),
        "issues_by_severity": by_severity,
        "dealers_with_issues": int((df["issue_count"] > 0).sum()),
    }


def run_pipeline() -> dict:
    """Full pipeline: load -> parse -> rules -> summary -> output."""
    df = load_dealer_data()
    df = parse_dates(df)
    df_enriched, issues = apply_rules(df)
    summary = compute_summary(df_enriched, issues)

    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Serialize for JSON (convert dates and NaN)
    records = df_enriched.copy()
    if "last_order_date" in records.columns:
        records["last_order_date"] = records["last_order_date"].astype(str)
    records = records.replace({pd.NA: None}).to_dict(orient="records")

    result = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "issues": issues,
        "dealers": records,
    }

    out_path = output_dir / RESULTS_JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    run_pipeline()
    print("Processing complete. Output written to", PROJECT_ROOT / OUTPUT_DIR / RESULTS_JSON)
