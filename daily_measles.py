import pandas as pd
import numpy as np
import json
import requests
import re
from datetime import date, timedelta
from io import StringIO
from epiweeks import Week

# --- Load JHU Measles Data ---
url = "https://raw.githubusercontent.com/CSSEGISandData/measles_data/main/measles_county_all_updates.csv"
measles_data = pd.read_csv(url)
measles_data[['county', 'state']] = measles_data['location_name'].str.split(', ', expand=True)
measles_data = measles_data.rename(columns={'value': 'cases'}).drop(columns=['location_type'])
measles_data['county'] = measles_data['county'].str.upper()
measles_data['state'] = measles_data['state'].str.upper()
measles_data['date'] = pd.to_datetime(measles_data['date'])
measles_data['mmwr_week_start'] = measles_data['date'].apply(lambda dt: Week.fromdate(dt).startdate())

# --- Full state list with 2-letter codes ---
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

# --- Generate all MMWR weeks in 2025 to today ---
start_date = date(2025, 1, 1)
end_date = date.today()
all_weeks = sorted({Week.fromdate(start_date + timedelta(days=i)).startdate() for i in range((end_date - start_date).days + 1)})

# --- Full grid: all states × all MMWR weeks ---
full_grid = pd.MultiIndex.from_product(
    [state_codes['state'].unique(), all_weeks],
    names=['state', 'mmwr_week_start']
).to_frame(index=False)

# --- Merge with original data
measles_data_complete = pd.merge(full_grid, measles_data, on=['state', 'mmwr_week_start'], how='left')
measles_data_complete['date'] = measles_data_complete['date'].fillna(measles_data_complete['mmwr_week_start'])
measles_data_complete['cases'] = measles_data_complete['cases'].fillna(0).astype(int)
measles_data_complete['county'] = measles_data_complete['county'].fillna('UNKNOWN')
measles_data_complete = pd.merge(measles_data_complete, state_codes, on='state', how='left')

# --- Collapse NYC and NY into single "NEW YORK" entry ---
grouped = measles_data_complete.groupby(['state', 'mmwr_week_start'])[['cases']].sum().reset_index()
ny_data = grouped[grouped['state'].isin(['NEW YORK', 'NEW YORK CITY'])]
ny_combined = ny_data.groupby('mmwr_week_start')['cases'].sum().reset_index()
ny_combined['state'] = 'NEW YORK'
grouped = grouped[~grouped['state'].isin(['NEW YORK', 'NEW YORK CITY'])]
grouped = pd.concat([grouped, ny_combined], ignore_index=True)
measles_data_complete = pd.merge(grouped, state_codes, on='state', how='left')
measles_data_complete['mmwr_week_start'] = pd.to_datetime(measles_data_complete['mmwr_week_start'])

# --- Summarize 2025 state-level totals ---
state_summary = (
    measles_data_complete.groupby('state', as_index=False)['cases'].sum()
    .assign(State=lambda df: df['state'].str.title())
    .loc[:, ['State', 'cases']]
    .rename(columns={'cases': '2025 Cases'})
)

# --- 2024 Data ---
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
states_2024_df = states_2024_df.groupby('State', as_index=False).sum()
states_2024_df.loc[states_2024_df['State'] == 'New York City', 'State'] = 'New York'
states_2024_df = states_2024_df.groupby('State', as_index=False).sum()

# --- Comparison and JSON export ---
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

# --- Write outputs
with open("YearlyComparison.json", "w") as f:
    json.dump(json_list, f, indent=2)

measles_data_complete.to_csv("USMeaslesCases.csv", index=False)

# --- CDC JSON cleaning
cdc_url = "https://www.cdc.gov/wcms/vizdata/measles/MeaslesCasesHospWeekly2025.json"
response = requests.get(cdc_url)
cdc_data = response.json()

cleaned_data = {}

for key, value in cdc_data.items():
    key_clean = key.lower().strip()
    if key_clean == "total_cases":
        cleaned_data["total_cases"] = int(value)
    elif key_clean == "total_deaths":
        cleaned_data["total_deaths"] = int(value)
    elif key_clean == "us_hospitalizations_in_2024":
        match = re.search(r"(\d+)%", value)
        if match:
            cleaned_data["hospitalized_pct"] = int(match.group(1)) / 100
    elif key_clean == "cases_hospitalized":
        match = re.search(r"\((\d+)\s+of", value)
        if match:
            cleaned_data["hospitalized_cases"] = int(match.group(1))
        pct_match = re.search(r"(\d+)%", value)
        if pct_match and "hospitalized_pct" not in cleaned_data:
            cleaned_data["hospitalized_pct"] = int(pct_match.group(1)) / 100
    elif isinstance(value, str) and "%" in value:
        pct_match = re.search(r"(\d+)%", value)
        if pct_match:
            cleaned_data[key_clean] = int(pct_match.group(1)) / 100

# --- Write CDC cleaned data
pd.DataFrame([cleaned_data]).to_csv("USMeaslesCasesDetails.csv", index=False)


# --- CDC Weekly Rash-Onset Data ---
cdc_weekly_url = "https://www.cdc.gov/wcms/vizdata/measles/MeaslesCasesWeekly.json"
cdc_weekly = requests.get(cdc_weekly_url).json()

if isinstance(cdc_weekly, list):
    df_cdc_weekly = pd.DataFrame(cdc_weekly)
elif isinstance(cdc_weekly, dict):
    # Common CDC WCMS patterns
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

# Normalize likely column names
def pick(colnames, candidates):
    low = {c.lower().strip(): c for c in colnames}
    for cand in candidates:
        if cand in low:
            return low[cand]
    return None

date_col = pick(df_cdc_weekly.columns, [
    "week start date", "week_start_date", "mmwr_week_start", "week", "weekstart"
])
cases_col = pick(df_cdc_weekly.columns, [
    "cases", "weekly cases", "weekly_cases", "count", "value"
])

if not date_col or not cases_col:
    raise ValueError(f"Could not find date/cases columns. Got: {list(df_cdc_weekly.columns)}")

df_cdc_weekly = df_cdc_weekly[[date_col, cases_col]].rename(
    columns={date_col: "mmwr_week_start", cases_col: "cases"}
)

df_cdc_weekly["mmwr_week_start"] = pd.to_datetime(df_cdc_weekly["mmwr_week_start"], errors="coerce")
df_cdc_weekly["cases"] = pd.to_numeric(df_cdc_weekly["cases"], errors="coerce").fillna(0).astype(int)

# Filter to 2025 MMWR year: 2024-12-29 → 2025-12-27
start_2025 = pd.Timestamp("2024-12-29")
end_2025   = pd.Timestamp("2025-12-27")
df_cdc_weekly_2025 = df_cdc_weekly[
    (df_cdc_weekly["mmwr_week_start"] >= start_2025) &
    (df_cdc_weekly["mmwr_week_start"] <= end_2025)
].sort_values("mmwr_week_start")

df_cdc_weekly_2025.to_csv("CDC_US_WeeklyRashOnset.csv", index=False)


