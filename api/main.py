"""
FastAPI backend: serves processed dealer data and issues to the Angular dashboard.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dealer Analytics API", version="1.0.0")

# Allow Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_FILE = PROJECT_ROOT / "output" / "processed_results.json"


def _run_pipeline():
    from scripts.run_validation_pipeline import run_pipeline
    return run_pipeline()


def load_results():
    """Load latest processed results from JSON."""
    if not RESULTS_FILE.exists():
        return None
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/results")
def get_results():
    """Full processed results (summary + issues + dealers)."""
    data = load_results()
    if data is None:
        return {"error": "No processed data. Run: python -m scripts.run_validation_pipeline"}
    return data


@app.get("/api/summary")
def get_summary():
    """Dashboard summary KPIs only."""
    data = load_results()
    if data is None:
        return {"error": "No processed data."}
    return data.get("summary", {})


@app.get("/api/issues")
def get_issues():
    """All detected issues/flaws for the dashboard."""
    data = load_results()
    if data is None:
        return []
    return data.get("issues", [])


@app.get("/api/dealers")
def get_dealers():
    """Dealer list with issue counts."""
    data = load_results()
    if data is None:
        return []
    return data.get("dealers", [])


@app.get("/api/outliers")
def get_outliers():
    """Outliers with confidence scores for human review (no auto-correction)."""
    data = load_results()
    if data is None:
        return []
    return data.get("outliers_for_human_review", [])


@app.post("/api/refresh")
def trigger_refresh():
    """Trigger data processing (run pipeline). For demo; in production use cron."""
    try:
        _run_pipeline()
        return {"status": "ok", "message": "Data refreshed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
