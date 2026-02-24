# JumpIQ – Complete Project Guide

> **Audience:** Team members, interviewers, and reviewers.
> **Purpose:** Detailed walkthrough of the system — what it does, how it works, why each piece exists, and how data flows end to end.

---

## 1. What This Project Is

JumpIQ is an **automotive intelligence platform** that values car dealerships for M&A transactions. This repository implements the **data validation and market insights** layer:

- **Ingest** dealership data from multiple sources (each reporting slightly different figures).
- **Cross-validate** data points against external benchmarks (state-level trends, seasonality).
- **Flag outliers** with confidence scores for human review (**no auto-correction**).
- **Connect external market signals** (competitor launches, supply chain disruptions, economic indicators) to internal business parameters and forecast impact.
- **Expose** everything via a REST API and an Angular dashboard.

---

## 2. End-to-End Data Flow

```
  ┌──────────────────────────────────────────────────────────┐
  │                     DATA SOURCES                         │
  │  source_dmv.csv   source_internal.csv  source_marketplace│
  └────────┬──────────────────┬──────────────────┬───────────┘
           │                  │                  │
           ▼                  ▼                  ▼
  ┌──────────────────────────────────────────────────────────┐
  │              1. INGESTION LAYER                          │
  │  scripts/ingestion.py                                    │
  │  - Load each source CSV                                  │
  │  - Validate schema (required columns, types)             │
  │  - Tag each row with source name                         │
  │  - Output: list of (source_name, DataFrame)              │
  │  - Output: list of validation issues (if any)            │
  └────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
  ┌──────────────────────────────────────────────────────────┐
  │              2. MERGE & VALIDATION LAYER                 │
  │  scripts/merge_and_validate.py                           │
  │  - Group by dealer_id across all sources                 │
  │  - Merge: median revenue & units across sources          │
  │  - Record std and source count per dealer                │
  │  - Flag CONFLICTS: if revenue varies > 10% across        │
  │    sources → conflict flag for human review               │
  │  - Output: merged DataFrame + conflict_flags list        │
  │                                                          │
  │  KEY PRINCIPLE: No auto-correction. Conflicts are        │
  │  flagged, not silently resolved.                         │
  └────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
  ┌──────────────────────────────────────────────────────────┐
  │              3. CROSS-VALIDATION LAYER                   │
  │  scripts/cross_validate.py                               │
  │                                                          │
  │  Benchmarks used:                                        │
  │  ┌──────────────────────────────────────────┐            │
  │  │ data/benchmarks/state_trends.csv         │            │
  │  │ (state_avg_revenue, state_std per state)  │            │
  │  ├──────────────────────────────────────────┤            │
  │  │ data/benchmarks/seasonality.csv          │            │
  │  │ (monthly revenue_index, units_index)      │            │
  │  └──────────────────────────────────────────┘            │
  │                                                          │
  │  - Compare each dealer's revenue to state average        │
  │  - Compute revenue_vs_state ratio (e.g. 1.08x)          │
  │  - Flag STATE_DEVIATION if outside 0.5x–2.0x band       │
  │  - Apply seasonality index to adjust revenue             │
  │  - Output: enriched DataFrame + deviation flags          │
  └────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
  ┌──────────────────────────────────────────────────────────┐
  │              4. OUTLIER DETECTION LAYER                  │
  │  scripts/outlier_detection.py                            │
  │                                                          │
  │  Method: IQR (Interquartile Range) on revenue & units    │
  │                                                          │
  │  For each dealer flagged as outlier:                     │
  │  - z-score (how many std from mean)                      │
  │  - confidence_score (0–1):                               │
  │      40% weight: strength of statistical deviation       │
  │      30% weight: multiple sources agree                  │
  │      30% weight: benchmark deviation confirms            │
  │                                                          │
  │  Output:                                                 │
  │  - List of outliers with dealer_id, metric, value,       │
  │    bounds, z_score, confidence_score, reason              │
  │  - Sorted by confidence (highest first)                  │
  │                                                          │
  │  KEY PRINCIPLE: Outliers are for HUMAN REVIEW only.      │
  │  No values are changed. No auto-correction.              │
  └────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
  ┌──────────────────────────────────────────────────────────┐
  │              5. MARKET SIGNALS LAYER                     │
  │  scripts/market_signals.py                               │
  │                                                          │
  │  Input: data/market_signals.json                         │
  │  Example signals:                                        │
  │  - Supply chain disruption → -2.0% revenue               │
  │  - Competitor launch (West) → -0.5% revenue              │
  │  - Economic indicator (rates) → +0.3% revenue            │
  │                                                          │
  │  Impact forecaster:                                      │
  │  - Sum signal effects → total revenue_delta_pct          │
  │  - Apply to total_revenue → revenue_impact (INR)         │
  │  - Output: impact summary with per-signal breakdown      │
  └────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
  ┌──────────────────────────────────────────────────────────┐
  │              6. INSIGHT GENERATION & OUTPUT              │
  │  scripts/run_validation_pipeline.py                      │
  │                                                          │
  │  Combines all layers into:                               │
  │  output/processed_results.json                           │
  │  ├── summary (KPIs, issue counts, market impact)         │
  │  ├── validation_issues (schema, conflicts, deviations)   │
  │  ├── outliers_for_human_review (with confidence scores)  │
  │  ├── dealers (merged records with enrichment columns)    │
  │  └── issues (dashboard-compatible format)                │
  └────────────────────────┬─────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
  ┌─────────────────────┐   ┌───────────────────────┐
  │    FastAPI Backend   │   │   Angular Dashboard   │
  │    api/main.py       │   │   dashboard/           │
  │                      │   │                       │
  │  GET /api/results    │◄──│  Calls API on load    │
  │  GET /api/summary    │   │                       │
  │  GET /api/issues     │   │  Sections:            │
  │  GET /api/dealers    │   │  - KPI cards           │
  │  GET /api/outliers   │   │  - Market impact       │
  │  POST /api/refresh   │   │  - Outliers (human)    │
  │                      │   │  - Issues list         │
  │  Swagger: /docs      │   │  - Dealers table       │
  └─────────────────────┘   └───────────────────────┘
```

---

## 3. File-by-File Explanation

### 3.1 Data Files (`data/`)

| File | Purpose |
|------|---------|
| `source_dmv.csv` | Simulates DMV registration data. Columns: dealer_id, dealer_name, state, revenue, units_sold, report_date, source. |
| `source_internal.csv` | Simulates internal dealership records. Same schema, slightly different revenue/units values. |
| `source_marketplace.csv` | Simulates online marketplace data. Same schema, slightly different values. D008 is missing here (not all sources have all dealers). |
| `benchmarks/state_trends.csv` | State-level benchmark: average revenue, units, std per state. Used for cross-validation. |
| `benchmarks/seasonality.csv` | Monthly seasonality index (1.0 = average). Revenue is adjusted by this index before comparison. |
| `market_signals.json` | External market signals: supply chain, competitor launches, economic indicators. Each has a revenue impact %. |
| `dealers_sample.csv` | Legacy sample data (single-source format). Kept for backward compatibility. |

### 3.2 Python Scripts (`scripts/`)

| File | Layer | What it does |
|------|-------|-------------|
| `ingestion.py` | Ingestion | Loads all `source_*.csv` files, validates schema (required columns, types, emptiness), returns tagged DataFrames + validation issues. |
| `merge_and_validate.py` | Validation | Merges by dealer_id using median across sources. Records std and source count. Flags revenue discrepancies (cv > 10%) as conflicts for human review. |
| `cross_validate.py` | Cross-validation | Compares dealer revenue to state averages from benchmarks. Applies seasonality. Flags state deviations (outside 0.5x–2.0x band). |
| `outlier_detection.py` | Outlier detection | IQR-based outlier detection on revenue and units. Computes confidence score (0–1) based on z-score strength, source count, and benchmark agreement. No auto-correction. |
| `market_signals.py` | Market signals | Loads external signals from JSON. Simple impact forecaster: sums revenue effects and applies to total. |
| `run_validation_pipeline.py` | Orchestrator | Runs all layers in sequence: ingest → merge → cross-validate → outlier → market signals → output JSON. Main entry point for cron/scheduler. |
| `config.py` | Config | Thresholds for the legacy single-source pipeline (margin %, turnover days, inactivity). |
| `process_data.py` | Legacy | Single-source ETL + rules (used before multi-source pipeline was added). Still works standalone. |
| `run_cron.py` | Legacy | Entry point for the legacy single-source pipeline. |

### 3.3 API (`api/`)

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/results` | GET | Full processed output (summary + issues + dealers + outliers) |
| `/api/summary` | GET | KPI summary only (total dealers, revenue, units, issue/outlier counts, market impact) |
| `/api/issues` | GET | All validation issues and flags |
| `/api/dealers` | GET | Merged dealer records with enrichment columns |
| `/api/outliers` | GET | Outliers for human review (sorted by confidence score, highest first) |
| `/api/refresh` | POST | Triggers the full validation pipeline and refreshes output |
| `/docs` | GET | Auto-generated Swagger / OpenAPI docs |

### 3.4 Dashboard (`dashboard/`)

| Section | What it shows |
|---------|--------------|
| **KPI cards** | Total dealers, total revenue, total units, issues/outliers count |
| **Market impact** | External signals applied, revenue delta %, absolute revenue impact, per-signal breakdown |
| **Outliers for human review** | Each outlier: dealer_id, metric, value, z-score, confidence score (0–1), reason. High-confidence items highlighted. No auto-correction. |
| **Issues by severity** | Bar chart of critical / warning / info counts |
| **Validation issues & flags** | List: severity, dealer_id, message (schema errors, conflicts, deviations, outliers) |
| **Dealers table** | Merged data: ID, name, state, revenue, units, revenue vs state (ratio), issue count |
| **Refresh button** | Calls POST /api/refresh to re-run the pipeline and reload the dashboard |

---

## 4. Why Each Design Decision

### 4.1 Multi-source with median merge (not "pick latest" or "pick one")

JumpIQ ingests data from DMV, real estate, marketplaces, and internal records. These report **slightly different figures**. Using the **median** across sources:
- Is robust to a single outlier source.
- Doesn't silently pick one source over another.
- The **std** and **source count** are recorded, so conflicts surface naturally.

### 4.2 No auto-correction

The task says: *"Flags outliers with confidence scores for human review (not auto-correction)."* Every layer in this system:
- **Flags** issues, conflicts, deviations, and outliers.
- **Never** changes a value automatically.
- Writes everything to a review list with metadata (confidence, z-score, source count).

### 4.3 Confidence score (0–1) for prioritization

Not all outliers are equal. The confidence score weighs:
- **Statistical strength** (how far from normal): 40%
- **Source consistency** (do multiple sources agree?): 30%
- **Benchmark agreement** (does state-level data also flag this?): 30%

This lets reviewers focus on high-confidence items first.

### 4.4 Seasonality adjustment

Without seasonality, a dealer in December (high season) might look like an outlier vs a dealer in February (low season). The `seasonality.csv` index normalizes revenue before comparison.

### 4.5 Market signals → impact

External events (supply disruptions, new competitors, rate changes) affect dealership metrics. The system:
- Ingests signals as structured JSON.
- Applies simple percentage effects to revenue.
- Shows the **impact** on the dashboard so analysts see context alongside the data.

In production this could be replaced with elasticity models or ML.

---

## 5. How to Extend

| Want to... | Do this |
|-----------|---------|
| Add a new data source | Add a new CSV in `data/source_<name>.csv` with the same columns. Add filename to `SOURCE_FILES` in `scripts/ingestion.py`. |
| Change outlier thresholds | Adjust `k` parameter in `iqr_bounds()` in `scripts/outlier_detection.py` (default 1.5). |
| Add a new market signal | Add an entry to `data/market_signals.json` with `name`, `description`, and `effect_revenue_pct`. |
| Update state benchmarks | Edit `data/benchmarks/state_trends.csv` with new state averages. |
| Use ML for outlier detection | Replace or extend `detect_outliers()` in `scripts/outlier_detection.py` with Isolation Forest, DBSCAN, or Prophet. |
| Switch to a real database | Replace CSV reads with SQL queries in `ingestion.py`; replace JSON output with DB writes in `run_validation_pipeline.py`. |
| Add real-time ingestion | Replace file-based flow with Kafka consumers; each adapter becomes a stream processor. |
| Use Kaggle data | See `docs/KAGGLE_DATA.md` for column mapping and file placement. |

---

## 6. Architecture Diagram

See **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** for the full Mermaid diagram and per-component justification table.

---

## 7. Quick Reference

```
# Run pipeline
python -m scripts.run_validation_pipeline

# Start API
uvicorn api.main:app --reload --port 8000

# Start dashboard
cd dashboard && npm start

# API docs
http://localhost:8000/docs

# Dashboard
http://localhost:4200
```
