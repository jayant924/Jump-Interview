"""
Multi-source ingestion: load dealership data from multiple sources (DMV, internal, marketplace).
Each source can report slightly different figures; we tag and keep source for merge/validation.
"""
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

SOURCE_FILES = [
    "source_dmv.csv",
    "source_internal.csv",
    "source_marketplace.csv",
]

REQUIRED_COLUMNS = ["dealer_id", "dealer_name", "state", "revenue", "units_sold", "report_date", "source"]


def load_all_sources() -> list[tuple[str, pd.DataFrame]]:
    """Load each source file; return list of (source_name, df)."""
    out = []
    for f in SOURCE_FILES:
        path = DATA_DIR / f
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        name = f.replace(".csv", "")
        out.append((name, df))
    return out


def validate_schema(df: pd.DataFrame, source: str) -> list[dict]:
    """Check required columns and types; return list of validation issues."""
    issues = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append({"source": source, "code": "MISSING_COLUMN", "field": col, "message": f"Missing column: {col}"})
    if df.empty:
        issues.append({"source": source, "code": "EMPTY_SOURCE", "message": "Source has no rows"})
    for col in ["revenue", "units_sold"]:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            issues.append({"source": source, "code": "INVALID_TYPE", "field": col, "message": f"{col} must be numeric"})
    return issues


def ingest() -> tuple[list[tuple[str, pd.DataFrame]], list[dict]]:
    """
    Ingest all sources and run schema/completeness validation.
    Returns (list of (source_name, df)), list of validation_issues.
    """
    loaded = load_all_sources()
    all_issues = []
    for name, df in loaded:
        all_issues.extend(validate_schema(df, name))
    return loaded, all_issues
