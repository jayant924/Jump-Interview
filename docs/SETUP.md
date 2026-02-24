# Setup & Run Instructions

Step-by-step guide to get the system running on a fresh machine.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

---

## Step 1: Clone / Open the project

```powershell
cd "c:\Shorthills\ADK\AI Agent\Jump-Interview"
```

---

## Step 2: Set up Python virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> On Linux/macOS: `source venv/bin/activate`

---

## Step 3: Install Python dependencies

```powershell
pip install -r requirements.txt
```

This installs: pandas, numpy, openpyxl, fastapi, uvicorn.

---

## Step 4: Run the validation pipeline

```powershell
python -m scripts.run_validation_pipeline
```

**Expected output:**
```
Validation pipeline complete. Output: output/processed_results.json
```

This runs the full pipeline:
1. Ingests data from `data/source_dmv.csv`, `data/source_internal.csv`, `data/source_marketplace.csv`
2. Validates schema
3. Merges by dealer_id (median across sources), flags conflicts
4. Cross-validates against `data/benchmarks/state_trends.csv` and `seasonality.csv`
5. Detects outliers with confidence scores (for human review)
6. Applies market signals from `data/market_signals.json`
7. Writes `output/processed_results.json`

---

## Step 5: Start the API server

```powershell
uvicorn api.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify:** Open http://localhost:8000/docs to see API documentation.

**API endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /api/results` | Full output (summary + dealers + issues + outliers) |
| `GET /api/summary` | KPI summary only |
| `GET /api/issues` | Validation issues and flags |
| `GET /api/dealers` | Merged dealer records |
| `GET /api/outliers` | Outliers for human review (with confidence) |
| `POST /api/refresh` | Re-run pipeline and refresh data |

---

## Step 6: Set up and start the Angular dashboard

Open a **new terminal** (keep the API running):

```powershell
cd "c:\Shorthills\ADK\AI Agent\Jump-Interview\dashboard"
npm install
npm start
```

**Expected output:**
```
** Angular Live Development Server is listening on localhost:4200 **
```

**Open:** http://localhost:4200

---

## Step 7: Verify everything works

1. Dashboard should load with KPI cards, market impact, and dealer table.
2. Click **Refresh data** — this calls `POST /api/refresh`, re-runs the pipeline, and reloads the dashboard.
3. Visit http://localhost:8000/docs to test individual API endpoints.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'pandas'` | Activate venv: `.\venv\Scripts\Activate.ps1`, then `pip install -r requirements.txt` |
| `Cannot reach API` shown on dashboard | Make sure the API is running on port 8000 (`uvicorn api.main:app --reload --port 8000`) |
| `npm start` fails | Make sure Node.js 18+ is installed. Run `npm install` first in the `dashboard/` folder. |
| Pipeline shows 0 outliers | With 10 sample dealers, values are close enough that IQR doesn't flag them. Add more varied data or adjust thresholds in `outlier_detection.py`. |
| Dashboard shows empty data | Run `python -m scripts.run_validation_pipeline` first to generate `output/processed_results.json`. |

---

## Running on a schedule (Cron / Task Scheduler)

### Windows Task Scheduler

1. Open Task Scheduler → Create Task.
2. **Trigger:** Daily or every 1 hour.
3. **Action:** Start a program.
   - **Program:** `C:\Shorthills\ADK\AI Agent\Jump-Interview\venv\Scripts\python.exe`
   - **Arguments:** `-m scripts.run_validation_pipeline`
   - **Start in:** `C:\Shorthills\ADK\AI Agent\Jump-Interview`

### Linux/macOS (cron)

```cron
0 * * * * cd /path/to/Jump-Interview && /path/to/venv/bin/python -m scripts.run_validation_pipeline
```

---

## Quick commands cheat sheet

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Run pipeline
python -m scripts.run_validation_pipeline

# Start API (from project root)
uvicorn api.main:app --reload --port 8000

# Start dashboard (from dashboard/)
cd dashboard && npm start

# API docs
# http://localhost:8000/docs

# Dashboard
# http://localhost:4200
```
