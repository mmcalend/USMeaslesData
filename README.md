# Daily Measles Data Pipeline

This project automates daily processing of U.S. county-level measles data from [JHU Measles Tracking Team Data Repository at Johns Hopkins University](https://github.com/CSSEGISandData/measles_data).

## What it does

- Downloads the latest measles data
- Summarizes 2025 cases by state
- Compares to 2024 totals
- Outputs:
  - `USMeaslesCases.csv`
  - `YearlyComparison.json`

## Automation

Runs daily at 15:00 UTC using GitHub Actions.  
Also supports manual runs from the Actions tab.

## Files

- `daily_measles.R`: Main script
- `.github/workflows/measles-pipeline.yml`: Workflow file

## Contact

Maintained by [@mmcalend](https://github.com/mmcalend)
