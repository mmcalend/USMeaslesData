#  Daily Measles Data Pipeline

---

##  What It Does

-  Downloads the latest measles case data (daily)
-  Summarizes **2025** measles cases by U.S. state
-  Compares to **2024** totals using a custom table
-  Standardizes weeks using **MMWR week start dates**
-  Incorporates **CDC supplemental estimates** for hospitalizations and deaths
-  Outputs:
  - `USMeaslesCases.csv` — weekly cases per state
  - `YearlyComparison.json` — state-level comparison (2024 vs 2025)
  - `USMeaslesCasesDetails.csv` — cleaned summary data from CDC
  - `CDC_US_WeeklyRashOnset.csv` — CDC national rash-onset weekly measles counts for the 2025 MMWR year (2024-12-29 → 2025-12-27).

---

##  Automation

-  **Runs daily** at **15:00 UTC** via GitHub Actions
-  Supports **manual runs** via the GitHub Actions tab
-  All outputs are automatically committed to the [`USMeaslesData`](https://github.com/mmcalend/USMeaslesData) output repository

---

##  Files

| File                              | Description                          |
|-----------------------------------|--------------------------------------|
| `daily_measles.py`                | Main Python processing script        |
| `.github/workflows/measles-pipeline.yml` | GitHub Actions workflow config |
| `USMeaslesCases.csv`              | Output: Weekly state-level cases     |
| `YearlyComparison.json`           | Output: 2024 vs 2025 comparison      |
| `USMeaslesCasesDetails.csv`       | Output: Cleaned CDC estimates        |
| `CDC_US_WeeklyRashOnset.csv`	    | Output: National weekly rash-onset cases (CDC)|

maintaned by mmcalend@asu.edu
