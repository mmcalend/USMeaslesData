# daily_measles.py

import pandas as pd
import numpy as np
import json
from epiweeks import Week
from datetime import date, timedelta
from io import StringIO
import requests
import re

# --- Load JHU Measles Data ---
url = "https://raw.githubusercontent.com/CSSEGISandData/measles_data/main/measles_county_all_updates.csv"
measles_data = pd.read_csv(url)
measles_data[['county', 'state']] = measles_data['location_name'].str.split(', ', expand=True)
measles_data = measles_data.rename(columns={'value': 'cases'}).drop(columns=['location_type'])
measles_data['county'] = measles_data['county'].str.upper()
measles_data['state'] = measles_data['state'].str.upper()
measles_data['date'] = pd.to_datetime(measles_data['date'])

def get_mmwr_week_start(dt): return Week.fromdate(dt).startdate()
measles_data['mmwr_week_start'] = measles_data['date'].apply(get_mmwr_week_start)

state_codes = pd.DataFrame([
    # (abbreviated for brevity, use full list as in your code)
    ("ALABAMA", "AL"), ("ALASKA", "AK"), ("ARIZONA", "AZ"), ("NEW YORK CITY", "NY")
], columns=['state', 'code'])

# --- Generate all MMWR weeks ---
start_date = date(2025, 1, 1)
end_date = date.today()
all_weeks = sorted({Week.fromdate(start_date + timedelta(days=i)).startdate() for i in range((end_date - start_date).days + 1)})

# --- Full grid
full_state_list = state_codes['state'].unique()
full_grid = pd.MultiIndex.from_product([full_state_list, all_weeks], names=['state', 'mmwr_week_start']).to_frame(index=False)

# --- Merge with measles data
measles_data_complete = pd.merge(full_grid, measles_data, on=['state', 'mmwr_week_start'], how='left')
measles_data_complete['date'] = measles_data_complete['date'].fillna(measles_data_complete['mmwr_week_start'])
measles_data_complete['cases'] = measles_data_complete['cases'].fillna(0).astype(int)
measles_data_complete['county'] = measles_data_complete['county'].fillna('UNKNOWN')
measles_data_complete = pd.merge(measles_data_complete, state_codes, on='state', how='left')

# --- State totals for 2025
state_summary = measles_data_complete.groupby('state', as_index=False)['cases'].sum()
state_summary['State'] = state_summary['state'].str.title()
state_summary = state_summary[['State', 'cases']].rename(columns={'cases': '2025 Cases'})

# --- 2024 Data
states_2024 = """Alabama\t0
Alaska\t0
Arizona\t5
California\t15
Illinois\t67
Minnesota\t70
New York\t1
New York City\t14
Oregon\t31
Texas\t1
Washington\t6
..."""  # Complete as needed

states_2024_df = pd.read_csv(StringIO(states_2024), sep='\t', header=None, names=['State', '2024 Cases'])
states_2024_df['State'] = states_2024_df['State'].str.title()

# --- Comparison
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
