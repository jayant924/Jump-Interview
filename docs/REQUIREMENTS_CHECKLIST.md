# JumpIQ Requirements vs What's Built

> Requirement-by-requirement checklist with demo proof for each item.
> Use this to explain to the team exactly what's done and where to find it.

---

## Summary

| # | Requirement | Status | Key proof |
|---|-------------|--------|-----------|
| 1 | Multi-source ingestion (slightly different figures) | DONE | 3 source CSVs; D012 flagged with 28.1% revenue discrepancy |
| 2 | Cross-validation against benchmarks (state, seasonality) | DONE | D011 at 5.04x state avg; D012 at 0.46x; seasonality index applied |
| 3 | Outlier detection with confidence scores (no auto-correction) | DONE | D011 flagged: confidence 0.88, z=2.79; no values changed |
| 4 | Market signals connected to internal parameters + impact | DONE | 3 signals → -2.2% revenue delta → -57,321 impact |
| 5 | Architecture diagram with component justification | DONE | 6-layer Mermaid diagram + justification tables in ARCHITECTURE.md |
| Bonus | Running with Kaggle sample data | DOCUMENTED | Column mapping + instructions in KAGGLE_DATA.md |

**Pipeline output:** 7 issues (2 critical, 2 warning, 3 info) across 3 dealers, 2 outliers for human review, 5 validation issues, market impact with 3 signals.

---

## Requirement 1: Multi-Source Ingestion

> *"Ingests dealership data from multiple sources (each reporting slightly different figures)"*

### What's implemented

| Component | File | Description |
|-----------|------|-------------|
| Source files | `data/source_dmv.csv` | DMV registration data (15 dealers) |
| | `data/source_internal.csv` | Internal dealership records (15 dealers) |
| | `data/source_marketplace.csv` | Online marketplace data (14 dealers — D008 missing, simulating incomplete sources) |
| Schema validation | `scripts/ingestion.py` | Validates required columns (`dealer_id`, `dealer_name`, `state`, `revenue`, `units_sold`, `report_date`, `source`), checks types, flags empty sources |
| Merge | `scripts/merge_and_validate.py` | Groups by `dealer_id`, computes **median** revenue and units across sources (robust to one bad source). Records `revenue_std` and `revenue_source_count` per dealer. |
| Conflict detection | `scripts/merge_and_validate.py` | If coefficient of variation (std/median) exceeds 10% → flagged as `REVENUE_DISCREPANCY` for human review |

### Demo proof

- **D012 (Lone Star Auto):** DMV reports 42,000 / internal reports 58,000 / marketplace reports 35,000 → CV = **28.1%** → flagged as revenue discrepancy.
- **D014 (Sunshine Dealers):** DMV reports 340,000 / internal reports 280,000 / marketplace reports 390,000 → CV = **16.2%** → flagged.
- **D008 (Lakeside Motors):** Missing from marketplace source (only 2 sources) → system handles gracefully, merge still works.

### Why median (not average or "pick latest")

- Average is sensitive to one extreme source.
- "Pick latest" silently trusts one source over others.
- **Median** is robust: if 2 of 3 sources agree, the outlier source doesn't distort the result. The std tells you how much they disagreed.

---

## Requirement 2: Cross-Validation Against External Benchmarks

> *"Cross-validates data points against external benchmarks (state-level trends, seasonality)"*

### What's implemented

| Component | File | Description |
|-----------|------|-------------|
| State-level benchmarks | `data/benchmarks/state_trends.csv` | Average revenue, units, std per state (CA, TX, NY, WA, OH, FL, IL, MN, CO) |
| Seasonality factors | `data/benchmarks/seasonality.csv` | Monthly revenue index (1.0 = annual average; Jan=0.92, Dec=1.12, etc.) |
| State comparison | `scripts/cross_validate.py` | Computes `revenue_vs_state` ratio (dealer revenue / state avg revenue) per dealer |
| Deviation flag | `scripts/cross_validate.py` | If ratio < 0.5 or > 2.0 → flagged as `STATE_DEVIATION` |
| Seasonality adjustment | `scripts/cross_validate.py` | Divides revenue by month's seasonality index → `revenue_season_adj` (prevents flagging normal seasonal swings) |

### Demo proof

- **D011 (Golden State Motors, CA):** Revenue 580,000 vs CA avg 115,000 → ratio **5.04x** → flagged (way above state norm).
- **D012 (Lone Star Auto, TX):** Revenue 42,000 vs TX avg 92,000 → ratio **0.46x** → flagged (below state norm).
- **D014 (Sunshine Dealers, FL):** Revenue 340,000 vs FL avg 68,000 → ratio **5.00x** → flagged (way above state norm).
- **D001 (North Auto, CA):** Revenue 125,000 vs CA avg 115,000 → ratio **1.09x** → NOT flagged (within normal band).

### Why 0.5x–2.0x band

Configurable. Tight enough to catch meaningful deviations (5x state avg is clearly unusual) but loose enough to not flood reviewers with noise. Can be tuned per state or segment.

---

## Requirement 3: Outlier Detection with Confidence Scores (No Auto-Correction)

> *"Flags outliers with confidence scores for human review (not auto-correction)"*

### What's implemented

| Component | File | Description |
|-----------|------|-------------|
| IQR detection | `scripts/outlier_detection.py` | Computes IQR bounds (Q1 - 1.5×IQR, Q3 + 1.5×IQR) for revenue and units_sold. Values outside bounds = outlier. |
| Z-score | `scripts/outlier_detection.py` | Measures how many standard deviations from mean. Higher = stronger signal. |
| Confidence scorer | `scripts/outlier_detection.py` → `compute_confidence()` | Score 0–1 composed of 3 factors (see breakdown below) |
| Output | `scripts/run_validation_pipeline.py` | Outliers written to `outliers_for_human_review` list, sorted by confidence (highest first) |
| No auto-correction | Entire pipeline | **No value is ever changed.** Outliers are flagged with metadata for a human to review and decide. |
| Dashboard | Dashboard "Outliers for human review" section | Shows dealer_id, metric, value, z-score, confidence score, reason |

### Confidence score breakdown

```
Confidence = (statistical_strength × 0.4) + (source_consistency × 0.3) + (benchmark_agreement × 0.3)

statistical_strength = min(1.0, |z_score| / 4.0)
  → z=2.79 gives 0.70; z=4+ gives 1.0

source_consistency:
  → 2+ sources available: 0.3 (median is reliable)
  → 1 source only: 0.1 (less trustworthy)

benchmark_agreement:
  → state deviation also flagged: 0.3 (independent confirmation)
  → no state deviation: 0.0
```

### Demo proof

**D011 (Golden State Motors):**

| Metric | Value | IQR bound (high) | Z-score | Sources | State flag | Confidence |
|--------|-------|-------------------|---------|---------|------------|------------|
| Revenue | 580,000 | 380,500 | 2.79 | 3 | YES (5.04x) | **0.88** |
| Units sold | 210 | 140.25 | 2.69 | 3 | YES (5.04x) | **0.87** |

Confidence is high (0.88) because all three signals agree:
1. Statistically far from normal (z=2.79)
2. All 3 sources confirm (they all report high revenue for D011)
3. State benchmark also flags it (5.04x CA average)

**This is the core deliverable.** A human reviewer sees: "D011 has 0.88 confidence outlier on revenue — z-score 2.79, all sources agree, state benchmark confirms. Review this dealer."

---

## Requirement 4: Market Signals Connected to Internal Parameters

> *"Connects external market signals (competitor launches, supply chain disruptions, economic indicators) to internal business parameters and forecasts impact"*

### What's implemented

| Component | File | Description |
|-----------|------|-------------|
| Signal definition | `data/market_signals.json` | 3 signals with name, description, and `effect_revenue_pct` |
| Impact forecaster | `scripts/market_signals.py` → `forecast_impact()` | Sums percentage effects, applies to total revenue, outputs per-signal breakdown |
| Output | `summary.market_impact` in JSON | `signals_applied`, `revenue_delta_pct`, `revenue_impact`, `impact_notes` |
| Dashboard | "Market impact (external signals)" section | Shows count, delta, impact, and per-signal bullet points |

### Demo proof

| Signal | Effect | Description |
|--------|--------|-------------|
| Supply chain disruption (Q1) | -2.0% | Parts shortage affecting delivery times |
| Competitor launch (Region West) | -0.5% | New entrant in selected regions |
| Economic indicator (rates) | +0.3% | Interest rate environment |
| **Total** | **-2.2%** | **Revenue impact: -57,321** |

### How it connects to internal parameters

- Total revenue from pipeline = 2,605,500
- Market signals predict -2.2% impact → -57,321
- Analysts see this alongside dealer data: "Revenue might drop by 57K due to supply chain + competitor + rates."
- In production: per-dealer or per-region signals; elasticity models instead of flat percentages.

---

## Requirement 5: Architecture Diagram with Component Justification

> *"Complete architecture diagram with component selection justification, covering data ingestion, validation, outlier detection, and insight generation layers"*

### What's implemented

| Deliverable | File |
|-------------|------|
| Mermaid architecture diagram (6 layers, all connections) | `docs/ARCHITECTURE.md` § 1 |
| Data Ingestion Layer — component justification table | `docs/ARCHITECTURE.md` § 2.1 |
| Validation Layer — component justification table | `docs/ARCHITECTURE.md` § 2.2 |
| Cross-Validation (Benchmarks) Layer — component justification table | `docs/ARCHITECTURE.md` § 2.3 |
| Outlier Detection Layer — component justification table | `docs/ARCHITECTURE.md` § 2.4 |
| Market Signals Layer — component justification table | `docs/ARCHITECTURE.md` § 2.5 |
| Insight Generation Layer — component justification table | `docs/ARCHITECTURE.md` § 2.6 |
| Data flow summary (6 steps) | `docs/ARCHITECTURE.md` § 3 |
| Technology mapping (example stack per layer) | `docs/ARCHITECTURE.md` § 4 |

### Architecture layers (summary)

```
1. Ingestion      → Source adapters, queue, raw store
2. Validation     → Schema, business rules, conflict resolution/merge
3. Cross-validation → State comparison, seasonality check, benchmark store
4. Outlier detection → Statistical detection, confidence scorer, human review store
5. Market signals → Signal ingestion, impact forecaster
6. Insights       → Aggregation/KPIs, alerts, API/dashboard
```

---

## Bonus: Kaggle Sample Data

> *"Running the same system with Sample Data from Kaggle would be a huge plus"*

### What's available

| Document | Content |
|----------|---------|
| `docs/KAGGLE_DATA.md` | Recommended datasets (US used car sales, US Sales Cars Dataset, US Motor Vehicle Registrations) |
| | Column mapping guide (Kaggle columns → system columns) |
| | Option A: Split one Kaggle CSV into 2–3 "sources" with small differences |
| | Option B: Use a single Kaggle file as one source |
| | Step-by-step instructions for file placement and running |

---

## All Documentation (linked from README)

| Document | Purpose | Audience |
|----------|---------|----------|
| `README.md` | Overview, quick start, project structure | First look |
| `docs/SETUP.md` | Step-by-step setup and run with troubleshooting | New team member |
| `docs/PROJECT_GUIDE.md` | Detailed walkthrough: flow diagrams, file-by-file, design decisions, extensibility | Team presentation |
| `docs/ARCHITECTURE.md` | Architecture diagram + component justification tables | Technical review / interview |
| `docs/KAGGLE_DATA.md` | How to use Kaggle data with this system | "Can it work with real data?" |
| `docs/REQUIREMENTS_CHECKLIST.md` | This file — requirement-by-requirement proof | "Is everything done?" |
