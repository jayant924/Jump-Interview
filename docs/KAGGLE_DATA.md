# Using Kaggle Sample Data with This System

Running the same validation & insights pipeline with **sample data from Kaggle** demonstrates proactiveness and fits JumpIQ’s evaluation (“Running the same system with Sample Data from Kaggle would be a huge plus”).

---

## Recommended Kaggle datasets

| Dataset | Use case | Link (search on Kaggle) |
|--------|----------|--------------------------|
| **US used car sales data** | Dealership-style sales, state/region | Search: “US used car sales data” (tsaustin) |
| **US Sales Cars Dataset** | US automotive sales | Search: “US Sales Cars Dataset” (juanmerinobermejo) |
| **US Motor Vehicle Registrations** | DMV-style registration data | Search: “US motor vehicle registrations” |

Download the CSV(s) from Kaggle (may require login and “Download” on the dataset page).

---

## How to plug Kaggle data into this repo

### Option A: Multi-source simulation (recommended)

The pipeline expects **multiple source files** (e.g. DMV, internal, marketplace) with **slightly different figures** for the same entities.

1. **Download one Kaggle dataset** (e.g. US used car sales or US Sales Cars).
2. **Split or duplicate with intentional differences:**
   - Create `data/source_dmv.csv`: subset or full CSV, ensure columns include **dealer_id** (or rename an ID column), **dealer_name**, **state**, **revenue** (or sales/price column), **units_sold** (or quantity), **report_date** (or date), and add a column **source** = `dmv`.
   - Create `data/source_internal.csv`: same rows but change **revenue** / **units_sold** by a few % (e.g. multiply by 0.98 or 1.02) to simulate “slightly different figures”; set **source** = `internal`.
   - Optionally `data/source_marketplace.csv` with another small variation; **source** = `marketplace`.
3. **Benchmarks:** Ensure `data/benchmarks/state_trends.csv` has one row per **state** in your data with columns: `state`, `state_avg_revenue`, `state_avg_units`, `state_std_revenue`, `period`. You can compute state-level averages from the Kaggle CSV and paste them in.
4. **Run the pipeline:**
   ```bash
   python -m scripts.run_validation_pipeline
   ```
5. Start API and dashboard as in the main README; you’ll see cross-validation vs state, outliers with confidence, and market impact.

### Option B: Single Kaggle file as one “source”

If you prefer a single file:

1. Put the Kaggle CSV in `data/` and name it e.g. `source_internal.csv`.
2. Add columns if needed: **dealer_id**, **dealer_name**, **state**, **revenue**, **units_sold**, **report_date**, **source** (= `internal`).
3. In `scripts/ingestion.py`, extend `SOURCE_FILES` or temporarily set:
   ```python
   SOURCE_FILES = ["source_internal.csv"]
   ```
4. Add or update `data/benchmarks/state_trends.csv` for states present in the file.
5. Run `python -m scripts.run_validation_pipeline`.

---

## Column mapping (Kaggle → this system)

| This system | Kaggle / typical names |
|------------|-------------------------|
| dealer_id | id, dealer_id, store_id, or create from name+state |
| dealer_name | name, dealer, store_name |
| state | state, State, region (if US state code) |
| revenue | revenue, sales, total_sales, price * quantity |
| units_sold | units_sold, quantity, vehicles_sold, count |
| report_date | date, report_date, sale_date (aggregate to month if needed) |
| source | Add column: dmv | internal | marketplace |

If the Kaggle dataset has different granularity (e.g. per transaction), aggregate to dealer-level (e.g. by dealer_id and month) before saving the CSVs in `data/`.

---

## What the system does with it

- **Ingestion:** Loads each `data/source_*.csv` and validates schema.
- **Merge:** Combines by dealer_id (median across sources); flags large discrepancies for human review.
- **Cross-validation:** Compares dealer revenue to `state_trends.csv` and applies `seasonality.csv` if present.
- **Outlier detection:** IQR-based flags with **confidence scores** (for human review; no auto-correction).
- **Market impact:** Reads `data/market_signals.json` and applies effect to summary metrics.
- **Output:** `output/processed_results.json` and the dashboard show validated dealers, issues, outliers with confidence, and market impact.

This matches the JumpIQ architecture: multi-source ingestion, cross-validation vs benchmarks, outliers with confidence for human review, and market signals connected to internal parameters.
