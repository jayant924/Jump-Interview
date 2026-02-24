"""
JumpIQ-style validation & insights pipeline:
  Multi-source ingestion -> Validation -> Merge -> Cross-validate (state, seasonality)
  -> Outlier detection (confidence scores for human review) -> Market signals impact -> Output.
Run: python -m scripts.run_validation_pipeline
Output: output/processed_results.json (used by API and dashboard).
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ingestion import ingest
from scripts.merge_and_validate import merge_sources
from scripts.cross_validate import cross_validate
from scripts.outlier_detection import detect_outliers
from scripts.market_signals import load_signals, forecast_impact


def run_pipeline() -> dict:
    # 1. Ingest multi-source
    loaded, ingest_issues = ingest()
    if not loaded:
        raise FileNotFoundError("No source files found in data/. Add source_dmv.csv, source_internal.csv, source_marketplace.csv.")

    # 2. Merge with conflict flags (no auto-correction)
    merged, conflict_flags = merge_sources(loaded)
    if merged.empty:
        return _empty_result(ingest_issues, conflict_flags)

    # 3. Cross-validate vs state trends and seasonality
    merged, crossval_issues = cross_validate(merged)

    # 4. Outlier detection with confidence scores (for human review)
    merged, outliers = detect_outliers(merged)

    # 5. Legacy-style issues for dashboard
    issues_legacy = _legacy_issues_for_dashboard(outliers, conflict_flags, crossval_issues)
    issues_by_severity = {}
    for i in issues_legacy:
        s = i.get("severity", "info")
        issues_by_severity[s] = issues_by_severity.get(s, 0) + 1
    dealers_with_issues = len(set(i["dealer_id"] for i in issues_legacy))

    # 6. Summary for insight layer (dashboard-compat)
    summary = {
        "total_dealers": len(merged),
        "total_revenue": round(float(merged["revenue"].sum()), 2),
        "total_units": int(merged["units_sold"].sum()),
        "total_profit": None,
        "avg_margin_pct": None,
        "validation_issues_count": len(ingest_issues) + len(conflict_flags) + len(crossval_issues),
        "issues_count": len(issues_legacy),
        "issues_by_severity": issues_by_severity,
        "dealers_with_issues": dealers_with_issues,
        "outliers_count": len(outliers),
        "outliers_for_human_review": len([o for o in outliers if o.get("confidence_score", 0) >= 0.3]),
    }

    # 7. Market signals impact
    signals = load_signals()
    impact = forecast_impact(signals, summary)
    summary["market_impact"] = impact

    # 8. Build output for API/dashboard: add issue_count per dealer
    records = merged.copy()
    records["report_date"] = records["report_date"].astype(str)
    dealer_issue_count = {}
    for i in issues_legacy:
        dealer_issue_count[i["dealer_id"]] = dealer_issue_count.get(i["dealer_id"], 0) + 1
    records["issue_count"] = records["dealer_id"].map(lambda x: dealer_issue_count.get(x, 0))
    records["region"] = records["state"]  # dashboard compat
    for c in records.columns:
        if "std" in c or "confidence" in c:
            records[c] = records[c].apply(lambda x: round(x, 4) if isinstance(x, (int, float)) and x == x else x)
    records = records.replace({float("nan"): None}).to_dict(orient="records")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": "validation_and_insights",
        "summary": summary,
        "validation_issues": ingest_issues + [{"code": "CONFLICT", **c} for c in conflict_flags] + crossval_issues,
        "outliers_for_human_review": sorted(outliers, key=lambda x: -x.get("confidence_score", 0)),
        "dealers": records,
        "issues": issues_legacy,
    }

    out_dir = PROJECT_ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "processed_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


def _legacy_issues_for_dashboard(outliers, conflict_flags, crossval_issues):
    """Format for existing dashboard: list of { dealer_id, code, severity, message }. No auto-correction."""
    issues = []
    for o in outliers:
        issues.append({
            "dealer_id": o["dealer_id"],
            "code": "OUTLIER_" + o.get("reason", "unknown").upper(),
            "severity": "critical" if o.get("confidence_score", 0) >= 0.6 else "warning",
            "message": f"{o['metric']} = {o['value']} (confidence: {o.get('confidence_score', 0):.2f})",
        })
    for c in conflict_flags:
        issues.append({
            "dealer_id": c["dealer_id"],
            "code": c.get("code", "CONFLICT"),
            "severity": "warning",
            "message": c.get("message", "Multi-source discrepancy"),
        })
    for x in crossval_issues:
        issues.append({
            "dealer_id": x["dealer_id"],
            "code": x.get("code", "CROSSVAL"),
            "severity": "info",
            "message": x.get("message", "Benchmark deviation"),
        })
    return issues


def _empty_result(ingest_issues, conflict_flags):
    out_dir = PROJECT_ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": "validation_and_insights",
        "summary": {"total_dealers": 0, "validation_issues_count": len(ingest_issues) + len(conflict_flags)},
        "validation_issues": ingest_issues + [{"code": "CONFLICT", **c} for c in conflict_flags],
        "outliers_for_human_review": [],
        "dealers": [],
        "issues": [],
    }
    with open(out_dir / "processed_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    run_pipeline()
    print("Validation pipeline complete. Output: output/processed_results.json")
