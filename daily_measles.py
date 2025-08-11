import pandas as pd
import numpy as np
import json
import requests
import re
from datetime import date, timedelta
from io import StringIO
from epiweeks import Week

# =========================
#  Load JHU Measles Data
# =========================
url = "https://raw.githubusercontent.com/CSSEGISandData/measles_data/main/measles_county_all_updates.csv"
measles_data = pd.read_csv(url)

# Split location into county/state, standardize, parse dates
measles_data[['county', 'state']] = measles_data['location_name'].str.split(', ', expand=True)
measles_data = measles_data.rename(columns={'value': 'cases'}).drop(columns=['location_type'])
measles_data['county'] = measles_data['county'].str.upper()
measles_data['state'] = measles_data['state'].str.upper()
measles_data['date'] = pd.to_datetime(measles_data['date'], errors="coerce")
measles_data['mmwr_week_start'] = measles_data['date'].apply(lambda dt: Week.fromdate(dt).startdate())

# =========================
#  Full state list (2-letter codes)
# =========================
state_codes = pd.DataFrame([
    ("ALABAMA", "AL"), ("ALASKA", "AK"), ("ARIZONA", "AZ"), ("ARKANSAS", "AR"),
    ("CALIFORNIA", "CA"), ("COLORADO", "CO"), ("CONNECTICUT", "CT"), ("DELAWARE", "DE"),
    ("DISTRICT OF COLUMBIA", "DC"), ("FLORIDA", "FL"), ("GEORGIA", "GA"), ("HAWAII", "HI"),
    ("IDAHO", "ID"), ("ILLINOIS", "IL"), ("INDIANA", "IN"), ("IOWA", "IA"), ("KANSAS", "KS"),
    ("KENTUCKY", "KY"), ("LOUISIANA", "LA"), ("MAINE", "ME"), ("MARYLAND", "MD"),
    ("MASSACHUSETTS", "MA"), ("MICHIGAN", "MI"), ("MINNESOTA", "MN"), ("MISSISSIPPI", "MS"),
    ("MISSOURI", "MO"), ("MONTANA", "MT"), ("NEBRASKA", "NE"), ("NEVADA", "NV"),
    ("NEW HAMPSHIRE", "NH"), ("NEW JERSEY", "NJ"), ("NEW MEXICO", "NM"), ("NEW YORK", "NY"),
    ("NEW YORK CITY", "NY"), ("NORTH CAROLINA", "NC"), ("NORTH DAKOTA", "ND"), ("OHIO", "OH"),
    ("OKLAHOMA", "OK"), ("OREGON", "OR"), ("PENNSYLVANIA", "PA"), ("RHODE ISLAND", "RI"),
    ("SOUTH CAROLINA", "SC"), ("SOUTH DAKOTA", "SD"), ("TENNESSEE", "TN"), ("TEXAS", "TX"),
    ("UTAH", "UT"), ("VERMONT", "VT"), ("VIRGINIA", "VA"), ("WASHINGTON", "WA"),
    ("WEST VIRGINIA", "WV"), ("WISCONSIN", "WI"), ("WYOMING", "WY")
], columns=['state', 'code'])

# =========================
#  Generate all MMWR weeks for 2025 MMWR year
#  (MMWR 2025 week 1 starts 2024-12-29; last week start is 2025-12-27)
# =========================
mmwr_start_2025 = Week(2025, 1).startdate()     # 2024-12-29 (Sunday)
mmwr_end_2025   = date(2025, 12, 27)            # last MMWR week start in 2025
today           = date.today()
grid_end        = min(today, mmwr_end_2025)

all_weeks = sorted({
    Week.fromdate(mmwr_start_2025 + timedelta(days=i)).startdate()
    for i in range((grid_end - mmwr_start_2025).days + 1)
})

# =========================
#  Build full state x week grid and merge
# =========================
full_grid = pd.MultiIndex.from_product(
    [state_codes['state'].unique(), all_weeks],
    names=['state', 'mmwr_week_start']
).to_frame(index=False)

measles_data_complete = pd.merge(full_grid, measles_data, on=['state', 'mmwr_week_start'], how='left')
measles_data_complete['date'] = measles_data_complete['date'].fillna(measles_data_complete['mmwr_week_start'])
measles_data_complete['cases'] = pd.to_numeric(measles_data_complete['cases'], errors="coerce").fillna(0).clip(lower=0).astype(int)
measles_data_complete['county'] = measles_data_complete['county'].fillna('UNKNOWN')
measles_data_complete = pd.merge(measles_data_complete, state_codes, on='state', how='left')

# =========================
#  Collapse NYC + NY into single "NEW YORK"
# =========================
grouped = measles_data_complete.groupby(['state', 'mmwr_week_start'])[['cases']].sum().reset_index()

ny_data = grouped[grouped['state'].isin(['NEW YORK', 'NEW YORK CITY'])]
ny_combined = ny_data.groupby('mmwr_week_start', as_index=False)['cases'].sum()
ny_combined['state'] = 'NEW YORK'

grouped = grouped[~grouped['state'].isin(['NEW YORK', 'NEW YORK CITY'])]
grouped = pd.concat([grouped, ny_combined], ignore_index=True)

measles_data_complete = pd.merge(grouped, state_codes, on='state', how='left')
measles_data_complete['mmwr_week_start'] = pd.to_datetime(measles_data_complete['mmwr_week_start'])

# Safety: one row per (state, week)
assert not measles_data_complete.duplicated(['state', 'mmwr_week_start']).any()

# =========================
#  Summarize 2025 state-level totals
# =========================
state_summary = (
    measles_data_complete.groupby('state', as_index=False)['cases'].sum()
    .assign(State=lambda df: df['state'].str.title())
    .loc[:, ['State', 'cases']]
    .rename(columns={'cases': '2025 Cases'})
)

# =========================
#  2024 Data (manual table, NYC merged into NY)
# =========================
states_2024 = """Alabama\t0
Alaska\t0
Arizona\t5
Arkansas\t0
California\t15
Colorado\t0
Connecticut\t0
Delaware\t0
District Of Columbia\t1
Florida\t12
Georgia\t6
Hawaii\t0
Idaho\t1
Illinois\t67
Indiana\t1
Iowa\t0
Kansas\t0
Kentucky\t0
Louisiana\t3
Maine\t0
Maryland\t1
Massachusetts\t1
Michigan\t6
Minnesota\t70
Mississippi\t0
Missouri\t3
Montana\t0
Nebraska\t0
Nevada\t0
New Hampshire\t2
New Jersey\t3
New Mexico\t2
New York\t1
New York City\t14
North Carolina\t1
North Dakota\t0
Ohio\t7
Oklahoma\t1
Oregon\t31
Pennsylvania\t4
Rhode Island\t0
South Carolina\t1
South Dakota\t1
Tennessee\t1
Texas\t1
Utah\t0
Vermont\t2
Virginia\t1
Washington\t6
West Virginia\t1
Wisconsin\t1
Wyoming\t0"""

states_2024_df = pd.read_csv(StringIO(states_2024), sep='\t', header=None, names=['State', '2024 Cases'])
states_2024_df['State'] = states_2024_df['State'].str.title()
# Merge NYC into NY for 2024 to match 2025 output
states_2024_df.loc[states_2024_df['State'] == 'New York City', 'State'] = 'New York'
states_2024_df = states_2024_df.groupby('State', as_index=False).sum()

# =========================
#  Comparison & JSON export
# =========================
comparison = pd.merge(states_2024_df, state_summary, on='State', how='left')
comparison['2025 Cases'] = comparison['2025 Cases'].fillna(0).astype(int)
comparison['Percent Change'] = np.where(
    comparison['2024 Cases'] == 0, np.nan,
    np.round((comparison['2025 Cases'] - comparison['2024 Cases']) / comparison['2024 Cases'] * 100, 4)
)

def change_indicator(row):
    if pd.isna(row['2024 Cases']):
        return np.nan
    elif row['2025 Cases'] > row['2024 Cases']:
        return "▲"
    elif row['2025 Cases'] < row['2024 Cases']:
        return "▼"
    return "➝"

comparison['Change Indicator'] = comparison.apply(change_indicator, axis=1)

def make_json_obj(row):
    base = {
        "State": row['State'],
        "2024 Cases": int(row['2024 Cases']),
        "2025 Cases": int(row['2025 Cases']),
        "Change Indicator": row['Change Indicator']
    }
    if not np.isnan(row['Percent Change']):
        base["Percent Change"] = row['Percent Change']
    return base

json_list = comparison.apply(make_json_obj, axis=1).tolist()

# =========================
#  Write core outputs
# =========================
with open("YearlyComparison.json", "w") as f:
    json.dump(json_list, f, indent=2)

measles_data_complete.to_csv("USMeaslesCases.csv", index=False)

# =========================
#  CDC summary (hospitalizations/deaths) cleaning
# =========================
cdc_summary_url = "https://www.cdc.gov/wcms/vizdata/measles/MeaslesCasesHospWeekly2025.json"
try:
    response = requests.get(cdc_summary_url, timeout=30)
    response.raise_for_status()
    cdc_data = response.json()
except Exception as e:
    print(f"[WARN] CDC summary fetch failed: {e}")
    cdc_data = {}

cleaned_data = {}

for key, value in cdc_data.items():
    key_clean = str(key).lower().strip()
    if key_clean == "total_cases":
        try:
            cleaned_data["total_cases"] = int(value)
        except Exception:
            pass
    elif key_clean == "total_deaths":
        try:
            cleaned_data["total_deaths"] = int(value)
        except Exception:
            pass
    elif key_clean == "us_hospitalizations_in_2024":
        match = re.search(r"(\d+)%", str(value))
        if match:
            cleaned_data["hospitalized_pct"] = int(match.group(1)) / 100
    elif key_clean == "cases_hospitalized":
        match = re.search(r"\((\d+)\s+of", str(value))
        if match:
            cleaned_data["hospitalized_cases"] = int(match.group(1))
        pct_match = re.search(r"(\d+)%", str(value))
        if pct_match and "hospitalized_pct" not in cleaned_data:
            cleaned_data["hospitalized_pct"] = int(pct_match.group(1)) / 100
    elif isinstance(value, str) and "%" in value:
        pct_match = re.search(r"(\d+)%", value)
        if pct_match:
            cleaned_data[key_clean] = int(pct_match.group(1)) / 100

pd.DataFrame([cleaned_data]).to_csv("USMeaslesCasesDetails.csv", index=False)

# =========================
#  CDC Weekly Rash-Onset (national epi-curve)
# =========================
def _pick(colnames, candidates):
    low = {c.lower().strip(): c for c in colnames}
    for cand in candidates:
        if cand in low:
            return low[cand]
    return None

cdc_weekly_url = "https://www.cdc.gov/wcms/vizdata/measles/MeaslesCasesWeekly.json"
try:
    r = requests.get(cdc_weekly_url, timeout=30)
    r.raise_for_status()
    cdc_weekly = r.json()
except Exception as e:
    print(f"[WARN] CDC weekly fetch failed: {e}")
    cdc_weekly = None

if cdc_weekly is not None:
    # Handle list/dict structures
    if isinstance(cdc_weekly, list):
        df_cdc_weekly = pd.DataFrame(cdc_weekly)
    elif isinstance(cdc_weekly, dict):
        for key in ("data", "dataset", "results", "rows"):
            if key in cdc_weekly and isinstance(cdc_weekly[key], list):
                df_cdc_weekly = pd.DataFrame(cdc_weekly[key])
                break
        else:
            if all(isinstance(v, list) for v in cdc_weekly.values()):
                df_cdc_weekly = pd.DataFrame(cdc_weekly)
            else:
                raise ValueError("Unrecognized CDC JSON structure for weekly data")
    else:
        raise ValueError("Unexpected JSON format from CDC weekly URL")

    # Robust column detection
    date_col = _pick(df_cdc_weekly.columns, [
        "week_start", "week start", "week start date", "week_start_date",
        "mmwr_week_start", "week", "weekstart"
    ])
    cases_col = _pick(df_cdc_weekly.columns, [
        "cases", "weekly cases", "weekly_cases", "count", "value"
    ])

    if not date_col or not cases_col:
        raise ValueError(f"Could not find date/cases columns. Got: {list(df_cdc_weekly.columns)}")

    df_cdc_weekly = df_cdc_weekly[[date_col, cases_col]].rename(
        columns={date_col: "mmwr_week_start", cases_col: "cases"}
    )
    df_cdc_weekly["mmwr_week_start"] = pd.to_datetime(df_cdc_weekly["mmwr_week_start"], errors="coerce", utc=False)
    df_cdc_weekly["cases"] = pd.to_numeric(df_cdc_weekly["cases"], errors="coerce").fillna(0).astype(int)

    # Filter to 2025 MMWR year
    start_2025 = pd.Timestamp("2024-12-29")
    end_2025   = pd.Timestamp("2025-12-27")
    df_cdc_weekly_2025 = df_cdc_weekly[
        (df_cdc_weekly["mmwr_week_start"] >= start_2025) &
        (df_cdc_weekly["mmwr_week_start"] <= end_2025)
    ].sort_values("mmwr_week_start").reset_index(drop=True)


    if not df_cdc_weekly_2025.empty and not (df_cdc_weekly_2025["mmwr_week_start"].dt.weekday == 6).all():
        print("[WARN] Some CDC week_start values are not Sundays.")

    df_cdc_weekly_2025.to_csv("CDC_US_WeeklyRashOnset.csv", index=False)
else:

    pd.DataFrame(columns=["mmwr_week_start", "cases"]).to_csv("CDC_US_WeeklyRashOnset.csv", index=False)

jhu_us_weekly = (
    measles_data_complete.groupby("mmwr_week_start", as_index=False)["cases"].sum()
    .sort_values("mmwr_week_start")
)
jhu_us_weekly.to_csv("JHU_US_WeeklyByReport.csv", index=False)

print("Done. Wrote: USMeaslesCases.csv, YearlyComparison.json, USMeaslesCasesDetails.csv, CDC_US_WeeklyRashOnset.csv, JHU_US_WeeklyByReport.csv")





