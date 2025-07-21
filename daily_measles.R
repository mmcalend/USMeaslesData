library(readr)
library(dplyr)
library(stringr)
library(tidyr)
library(MMWRweek)
library(jsonlite)

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

# --- 2024 state-level data ---
states_2024 <- "Alabama\t0\nAlaska\t0\nArizona\t5\nArkansas\t0\nCalifornia\t15\nColorado\t0\nConnecticut\t0\nDelaware\t0\nDistrict Of Columbia\t1\nFlorida\t12\nGeorgia\t6\nHawaii\t0\nIdaho\t1\nIllinois\t67\nIndiana\t1\nIowa\t0\nKansas\t0\nKentucky\t0\nLouisiana\t3\nMaine\t0\nMaryland\t1\nMassachusetts\t1\nMichigan\t6\nMinnesota\t70\nMississippi\t0\nMissouri\t3\nMontana\t0\nNebraska\t0\nNevada\t0\nNew Hampshire\t2\nNew Jersey\t3\nNew Mexico\t2\nNew York\t1\nNew York City\t14\nNorth Carolina\t1\nNorth Dakota\t0\nOhio\t7\nOklahoma\t1\nOregon\t31\nPennsylvania\t4\nRhode Island\t0\nSouth Carolina\t1\nSouth Dakota\t1\nTennessee\t1\nTexas\t1\nUtah\t0\nVermont\t2\nVirginia\t1\nWashington\t6\nWest Virginia\t1\nWisconsin\t1\nWyoming\t0"

states_2024_df <- read.table(
  text = states_2024, sep = "\t", header = FALSE,
  col.names = c("State", "2024 Cases"), stringsAsFactors = FALSE
)
names(states_2024_df)[2] <- "2024 Cases"

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
      TRUE ~ round((`2025 Cases` - `2024 Cases`) / `2024 Cases` * 100, 4)
    ),
    `Change Indicator` = case_when(
      is.na(`2024 Cases`) ~ NA_character_,
      `2025 Cases` > `2024 Cases` ~ "▲",
      `2025 Cases` < `2024 Cases` ~ "▼",
      TRUE ~ "➝"
    )
  )
# Ensure date column is Date type
measles_data <- measles_data %>%
  mutate(date = as.Date(date)) %>%
  mutate(
    mmwr_week = MMWRweek(date)$MMWRweek,
    mmwr_week_start = MMWRweek::MMWRweek2Date(MMWRyear = MMWRweek(date)$MMWRyear, 
                                              MMWRweek = MMWRweek(date)$MMWRweek)
  )

# --- Get all unique states and MMWR week start dates ---
all_states <- unique(measles_data$state)
all_weeks <- unique(measles_data$mmwr_week_start)

# --- Create full state-week grid ---
complete_grid <- expand.grid(
  state = all_states,
  mmwr_week_start = all_weeks,
  stringsAsFactors = FALSE
)

# --- Merge with measles data and fill in missing values with 0 cases ---
measles_data_complete <- complete_grid %>%
  left_join(measles_data, by = c("state", "mmwr_week_start")) %>%
  mutate(
    date = coalesce(date, mmwr_week_start),  # placeholder if missing
    cases = coalesce(cases, 0),
    county = coalesce(county, "UNKNOWN")  # optional
  )
# --- Format for JSON: remove "Percent Change" when 2024 Cases == 0 ---
YearlyComparison <- YearlyComparison %>%
  mutate(
    include_percent = !is.na(`Percent Change`)
  ) %>%
  rowwise() %>%
  mutate(
    json_obj = list({
      base <- list(
        State = State,
        `2024 Cases` = `2024 Cases`,
        `2025 Cases` = `2025 Cases`,
        `Change Indicator` = `Change Indicator`
      )
      if (include_percent) {
        base$`Percent Change` <- `Percent Change`
      }
      base
    })
  ) %>%
  pull(json_obj)

# --- Write outputs ---
write_json(YearlyComparison, "YearlyComparison.json", pretty = TRUE, auto_unbox = TRUE)
write_csv(measles_data_complete, "USMeaslesCases.csv")
