# Turbine data quality audit

Stage 1: read-only diagnostics. No rows were deleted, imputed or clipped.

CSV clock times explicitly mean Asia/Almaty. They are preserved without conversion to UTC; backend weather uses the same local hours.

## Overview

| Metric | Turbine 1 | Turbine 2 |
| --- | ---: | ---: |
| rows | 142360 | 149499 |
| period_start | 2023-03-11T00:00:00 | 2023-03-11T00:00:00 |
| period_end | 2026-01-31T23:50:00 | 2026-01-31T23:50:00 |
| exact_duplicate_rows_extra | 0 | 0 |
| duplicate_timestamps_extra | 0 | 0 |
| conflicting_timestamp_groups | 0 | 0 |
| invalid_or_missing_timestamps | 0 | 0 |
| expected_observations | 152352 | 152352 |
| missing_observations | 9992 | 2853 |
| gap_count | 67 | 178 |
| off_grid_rows | 0 | 0 |
| outside_expected_period_rows | 0 | 0 |
| backward_timestamp_steps | 0 | 0 |
| power_outside_0_1 | 0 | 0 |
| negative_wind_speed | 0 | 0 |

## Turbine 1

Source: `turbine 1.csv`. SHA-256: `c4c341582fb2dd348b7187f0128cff265fe055f469413871ebb5db50eef58b5b`.

Missing expected samples: 6.56%. Missing coverage includes leading and trailing intervals in the configured study period.

| Variable | Min | Max | NaN | Invalid numeric | Infinity | IQR flags | Constant runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| wind_speed | 0.0 | 22.97 | 0 | 0 | 0 | 0 | 0 |
| power | 0.0 | 1.0 | 0 | 0 | 0 | 0 | 235 |
| temperature | -19.26 | 43.48 | 0 | 0 | 0 | 0 | 0 |

### Largest missing intervals

| First missing sample | Last missing sample | Missing samples |
| --- | --- | ---: |
| 2024-05-18T03:50:00 | 2024-06-28T18:30:00 | 5993 |
| 2024-06-28T23:10:00 | 2024-07-17T17:10:00 | 2701 |
| 2025-10-03T10:50:00 | 2025-10-05T13:50:00 | 307 |
| 2025-05-23T19:00:00 | 2025-05-24T22:50:00 | 168 |
| 2023-10-07T08:30:00 | 2023-10-07T20:00:00 | 70 |
| 2025-03-31T10:40:00 | 2025-03-31T18:10:00 | 46 |
| 2024-10-15T10:20:00 | 2024-10-15T17:40:00 | 45 |
| 2023-07-26T09:50:00 | 2023-07-26T17:00:00 | 44 |
| 2025-04-08T10:40:00 | 2025-04-08T17:50:00 | 44 |
| 2025-06-17T10:30:00 | 2025-06-17T17:40:00 | 44 |

### Timestamp spacing

Minutes between sorted unique valid timestamps: 10.0: 142292, 20.0: 13, 30.0: 11, 40.0: 7, 50.0: 5, 70.0: 1, 80.0: 1, 110.0: 1, 120.0: 2, 130.0: 1, 140.0: 1, 170.0: 2, 190.0: 1, 230.0: 2, 290.0: 1, 310.0: 1, 330.0: 2, 340.0: 3, 350.0: 1, 360.0: 1, 450.0: 3, 460.0: 1, 470.0: 1, 710.0: 1, 1690.0: 1, 3080.0: 1, 27020.0: 1, 59940.0: 1.

### Source missing values

{"id": 0, "timestamp": 0, "wind_speed": 0, "power": 0, "temperature": 0}

### Parsed types

id: string, timestamp: datetime64[us], wind_speed: float64, power: float64, temperature: float64
.

## Turbine 2

Source: `turbine 2.csv`. SHA-256: `820578cd18bb557cd30c2e102f3ae5a386dfc6c489a5a15743339c2b017305e5`.

Missing expected samples: 1.87%. Missing coverage includes leading and trailing intervals in the configured study period.

| Variable | Min | Max | NaN | Invalid numeric | Infinity | IQR flags | Constant runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| wind_speed | 0.11 | 21.43 | 0 | 0 | 0 | 0 | 0 |
| power | 0.0 | 1.0 | 0 | 0 | 0 | 0 | 156 |
| temperature | -19.08 | 43.97 | 0 | 0 | 0 | 0 | 0 |

### Largest missing intervals

| First missing sample | Last missing sample | Missing samples |
| --- | --- | ---: |
| 2024-05-18T04:10:00 | 2024-05-20T13:20:00 | 344 |
| 2025-10-03T10:50:00 | 2025-10-05T13:50:00 | 307 |
| 2024-02-16T12:30:00 | 2024-02-17T18:30:00 | 181 |
| 2025-05-23T19:00:00 | 2025-05-24T22:50:00 | 168 |
| 2023-04-14T15:50:00 | 2023-04-15T17:50:00 | 157 |
| 2023-06-06T12:50:00 | 2023-06-07T01:10:00 | 75 |
| 2023-10-07T08:30:00 | 2023-10-07T20:00:00 | 70 |
| 2025-04-04T10:00:00 | 2025-04-04T19:40:00 | 59 |
| 2024-05-28T10:50:00 | 2024-05-28T18:20:00 | 46 |
| 2025-03-31T10:40:00 | 2025-03-31T18:10:00 | 46 |

### Timestamp spacing

Minutes between sorted unique valid timestamps: 10.0: 149320, 20.0: 58, 30.0: 22, 40.0: 9, 50.0: 11, 60.0: 10, 70.0: 9, 80.0: 2, 90.0: 1, 100.0: 3, 110.0: 3, 120.0: 2, 130.0: 1, 150.0: 1, 160.0: 3, 170.0: 3, 190.0: 2, 200.0: 1, 210.0: 1, 220.0: 3, 230.0: 3, 240.0: 2, 250.0: 1, 290.0: 2, 330.0: 1, 340.0: 2, 350.0: 3, 360.0: 1, 390.0: 2, 410.0: 1, 450.0: 3, 460.0: 2, 470.0: 2, 600.0: 1, 710.0: 1, 760.0: 1, 1580.0: 1, 1690.0: 1, 1820.0: 1, 3080.0: 1, 3450.0: 1.

### Source missing values

{"id": 0, "timestamp": 0, "wind_speed": 0, "power": 0, "temperature": 0}

### Parsed types

id: string, timestamp: datetime64[us], wind_speed: float64, power: float64, temperature: float64
.

## Interpretation and next stage

- Gaps are absent slots on the configured 10-minute grid, not fabricated measurements. Full intervals and monthly counts are in data_quality.json.
- Duplicate counts are extra occurrences. Conflicting timestamp groups have different parsed sensor values at the same timestamp.
- NaN counts include missing tokens and unparseable numbers; infinities are counted separately. Finite values alone determine ranges and IQR fences.
- Wind and power outlier flags use Q1 - 3 IQR and Q3 + 3 IQR for diagnostics only. Temperature IQR flags are disabled: warm nights around +15°C in March or +1.4°C in January are not anomalies for this southern region. Finite temperatures are retained. Do not reuse full-history thresholds in validation-fold cleaning.
- Constant runs require at least 36 equal finite samples at consecutive 10-minute timestamps. Gaps, invalid readings and duplicate timestamps break runs. Zero-power runs may reflect calm wind or shutdowns, so flags alone do not justify deletion.
- The next stage is visual EDA and hourly aggregation, with explicit coverage counts and a documented cleaning policy. Keep future wind standard deviation and other observed-only diagnostics out of production predictors.
- This audit does not evaluate forecasts. The supplied CSVs cannot establish genuine February forecast performance.
- Backend provides real archived forecasts from Open-Meteo Previous Runs / Historical Forecast API, already mapped to wind_speed and temperature in Asia/Almaty. ML performs no weather HTTP requests, wind-height parsing or provider-field renaming.
