library(readr)
library(dplyr)
library(stringr)
library(tidyr)
library(jsonlite)
library(bigrquery)

# --- Load JHU Measles Data ---
url <- "https://raw.githubusercontent.com/CSSEGISandData/measles_data/main/measles_county_all_updates.csv"
measles_data <- read_csv(url, show_col_types = FALSE)

# --- Clean data ---
measles_data <- measles_data %>%
  separate(location_name, into = c("county", "state"), sep = ", ", remove = TRUE) %>%
  rename(cases = value) %>%
  select(-location_type) %>%
  mutate(
    county = str_to_upper(county),
    state = str_to_upper(state)
  )

# --- Manually entered 2024 state-level data ---
states_2024 <- "Alabama\t0\nAlaska\t0\nArizona\t5\nArkansas\t0\nCalifornia\t15\nColorado\t0\nConnecticut\t0\nDelaware\t0\nDistrict Of Columbia\t1\nFlorida\t12\nGeorgia\t6\nHawaii\t0\nIdaho\t1\nIllinois\t67\nIndiana\t1\nIowa\t0\nKansas\t0\nKentucky\t0\nLouisiana\t3\nMaine\t0\nMaryland\t1\nMassachusetts\t1\nMichigan\t6\nMinnesota\t70\nMississippi\t0\nMissouri\t3\nMontana\t0\nNebraska\t0\nNevada\t0\nNew Hampshire\t2\nNew Jersey\t3\nNew Mexico\t2\nNew York\t1\nNew York City\t14\nNorth Carolina\t1\nNorth Dakota\t0\nOhio\t7\nOklahoma\t1\nOregon\t31\nPennsylvania\t4\nRhode Island\t0\nSouth Carolina\t1\nSouth Dakota\t1\nTennessee\t1\nTexas\t1\nUtah\t0\nVermont\t2\nVirginia\t1\nWashington\t6\nWest Virginia\t1\nWisconsin\t1\nWyoming\t0"

states_2024_df <- read.table(
  text = states_2024, sep = "\t", header = FALSE,
  col.names = c("State", "2024 Cases"), stringsAsFactors = FALSE
)

# --- Summarize 2025 data ---
state_summary <- measles_data %>%
  group_by(state) %>%
  summarise(`2025 Cases` = sum(cases, na.rm = TRUE), .groups = "drop") %>%
  mutate(State = str_to_title(state)) %>%
  select(State, `2025 Cases`)

# --- Join and calculate changes ---
YearlyComparison <- left_join(states_2024_df, state_summary, by = "State") %>%
  mutate(
    `2025 Cases` = coalesce(`2025 Cases`, 0),
    `Percent Change` = case_when(
      is.na(`2024 Cases`) | `2024 Cases` == 0 ~ NA_real_,
      TRUE ~ ((`2025 Cases` - `2024 Cases`) / `2024 Cases`) * 100
    ),
    `Change Indicator` = case_when(
      is.na(`2024 Cases`) ~ NA_character_,
      `2025 Cases` > `2024 Cases` ~ "▲",
      `2025 Cases` < `2024 Cases` ~ "▼",
      TRUE ~ "➝"
    )
  )

# --- Write outputs ---
write_json(YearlyComparison, "measles_state_comparison.json", pretty = TRUE, auto_unbox = TRUE)
write_csv(measles_data, "USMeaslesCases.csv")

# --- Upload to BigQuery ---
bq_auth(path = "service-account.json")
bq_table_upload(
  x = bq_table("ho-measles-459023.measles_risk_assessment.USMeaslesCases"),  # <-- Replace with your actual GCP values
  values = "USMeaslesCases.csv",
  source_format = "CSV",
  write_disposition = "WRITE_TRUNCATE"
)
