# Dealership Data Validation & Market Insights

Built for the JumpIQ evaluation task. The system ingests dealership data from multiple sources, validates and cross-checks it against benchmarks, flags outliers for human review (with confidence scores), and shows market signal impact — all visible in a dashboard.

I come from a backend background and don't have deep Python experience, so I used AI tooling (Cursor + Claude) to help implement the data processing scripts. The architecture design, data flow thinking, and component decisions are mine — the AI helped me write the pandas/numpy code faster.

## How to run

```
# setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# run the pipeline (generates output/processed_results.json)
python -m scripts.run_validation_pipeline

# start the API
uvicorn api.main:app --reload --port 8000

# in another terminal, start the dashboard
cd dashboard
npm install
npm start
```

Dashboard: http://localhost:4200
API docs: http://localhost:8000/docs

## What it does

**The pipeline runs in 5 steps:**

1. **Ingest** — Loads dealer data from 3 sources (`data/source_dmv.csv`, `source_internal.csv`, `source_marketplace.csv`). Each has slightly different revenue/units for the same dealers. Validates schema.

2. **Merge** — Groups by `dealer_id`, takes median across sources. If sources disagree by more than 10% (coefficient of variation), it's flagged as a conflict for human review. No values are auto-corrected.

3. **Cross-validate** — Compares each dealer's revenue to their state average (`data/benchmarks/state_trends.csv`). Applies seasonality adjustment (`data/benchmarks/seasonality.csv`). Flags dealers outside 0.5x–2.0x of state norm.

4. **Outlier detection** — Uses IQR method on revenue and units. Each outlier gets a confidence score (0 to 1) based on: how far from normal statistically (40%), whether multiple sources confirm it (30%), and whether state benchmarks also flag it (30%). Outliers go to a review list — nothing is auto-corrected.

5. **Market signals** — Reads external signals from `data/market_signals.json` (supply chain disruption, competitor launches, economic indicators). Calculates revenue impact and shows it in the summary.

Output goes to `output/processed_results.json`, which the FastAPI backend serves to the Angular dashboard.

## What the dashboard shows

- KPI cards (dealers, revenue, units, issue count)
- Market impact section (which signals, what % effect)
- Outliers for human review (with confidence scores)
- Validation issues (source conflicts, state deviations)
- Dealer table (merged data, revenue vs state ratio)

## Current demo results

With the sample data (15 dealers across 3 sources):
- D011 (Golden State Motors) flagged as outlier — revenue 580K, confidence 0.88, 5x California state average
- D012 (Lone Star Auto) — 28% revenue discrepancy across sources (DMV: 42K, internal: 58K, marketplace: 35K)
- D014 (Sunshine Dealers) — 16% revenue discrepancy + 5x Florida state average
- 3 market signals applied → -2.2% projected revenue impact

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full diagram and why I picked each component.

## Project structure

```
scripts/
  ingestion.py              # load + validate source CSVs
  merge_and_validate.py     # merge by dealer_id, flag conflicts
  cross_validate.py         # compare vs state benchmarks + seasonality
  outlier_detection.py      # IQR + confidence scoring
  market_signals.py         # external signal impact
  run_validation_pipeline.py # orchestrator — runs everything

data/
  source_dmv.csv            # source 1
  source_internal.csv       # source 2
  source_marketplace.csv    # source 3
  benchmarks/               # state trends + seasonality CSVs
  market_signals.json       # external signals config

api/main.py                 # FastAPI backend
dashboard/                  # Angular frontend
output/                     # generated JSON (pipeline output)
```

## Using different data

Drop your CSVs in `data/` with columns: `dealer_id, dealer_name, state, revenue, units_sold, report_date, source`. Update `SOURCE_FILES` in `scripts/ingestion.py` if you change filenames. Update `data/benchmarks/state_trends.csv` with relevant state averages.

Works with Kaggle datasets too (e.g. US used car sales) — just map columns to the expected format above.
