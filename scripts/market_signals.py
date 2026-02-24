"""
Load external market signals and estimate their revenue impact.
"""
from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SIGNALS_PATH = PROJECT_ROOT / "data" / "market_signals.json"


def load_signals() -> list[dict]:
    path = SIGNALS_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("signals", [])


def forecast_impact(signals: list[dict], summary: dict) -> dict:
    """
    Simple impact forecaster: apply signal deltas to high-level KPIs.
    In production: model or rules per signal type (competitor launch, supply, economic).
    """
    revenue_delta_pct = 0.0
    impact_notes = []
    for s in signals:
        effect = s.get("effect_revenue_pct", 0)
        revenue_delta_pct += effect
        impact_notes.append({
            "signal": s.get("name", "unknown"),
            "effect_revenue_pct": effect,
            "description": s.get("description", ""),
        })

    total_revenue = summary.get("total_revenue", 0) or 0
    impact_revenue = total_revenue * (revenue_delta_pct / 100)
    return {
        "signals_applied": len(signals),
        "revenue_delta_pct": round(revenue_delta_pct, 2),
        "revenue_impact": round(impact_revenue, 2),
        "impact_notes": impact_notes,
    }
