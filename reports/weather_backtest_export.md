# Weather export for the February backtest

Generated 2026-09-23 10:16 UTC by `python -m backend.scripts.export_weather_backtest`.

## Source

- Endpoint: `https://single-runs-api.open-meteo.com/v1/forecast` (Open-Meteo **Single Runs API**)
- Model: `ecmwf_ifs` (ECMWF IFS HRES 9 km), variables `wind_speed_100m` (fallback `wind_speed_10m`), `temperature_2m`, `wind_speed_unit=ms`
- Timezone: `timezone=Asia/Almaty` in every request; the API confirmed `Asia/Almaty` (UTC+05:00) and every timestamp in the CSV carries the `+05:00` offset.
- Not used: Historical Forecast API. It stitches the first hours of successive runs into one series, so a +30 h target would come from a run issued after the origin (look-ahead).

## Leakage rule

For each origin (00:00 Asia/Almaty) the newest run with `run_init + 6 h <= forecast_origin` is used (6 h = upper bound of the publication delay for global models per Open-Meteo docs). If it is not archived, earlier real runs are tried; nothing is ever interpolated or synthesised.

`weather_valid_time = run_init + 6 h` — the conservative moment the forecast became available. The export asserts `weather_valid_time <= forecast_origin <= timestamp` for every row.

## Coverage

- Origins requested: **29** (2026-01-31 .. 2026-02-28)
- Fully covered (both turbines): **29**
- Partially covered: **0**
- Missing: **0**
- Rows exported: **2784** (48 hourly targets × turbine × origin)
- Hours using the 10 m wind fallback: **0**
- Blocks served by an older run than the newest allowed: **0**

Grid points returned by the API:

- Turbine 1: 43.6204, 78.4789
- Turbine 2: 43.6204, 78.4789

Both turbines are ~350 m apart and may fall into the same model grid cell, in which case their weather is identical.

## Per origin

| forecast_origin | run used (UTC) | weather_valid_time | lead time of targets | status |
| --- | --- | --- | --- | --- |
| 2026-01-31T00:00:00+05:00 | 2026-01-30 12:00 | 2026-01-30T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-01T00:00:00+05:00 | 2026-01-31 12:00 | 2026-01-31T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-02T00:00:00+05:00 | 2026-02-01 12:00 | 2026-02-01T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-03T00:00:00+05:00 | 2026-02-02 12:00 | 2026-02-02T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-04T00:00:00+05:00 | 2026-02-03 12:00 | 2026-02-03T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-05T00:00:00+05:00 | 2026-02-04 12:00 | 2026-02-04T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-06T00:00:00+05:00 | 2026-02-05 12:00 | 2026-02-05T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-07T00:00:00+05:00 | 2026-02-06 12:00 | 2026-02-06T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-08T00:00:00+05:00 | 2026-02-07 12:00 | 2026-02-07T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-09T00:00:00+05:00 | 2026-02-08 12:00 | 2026-02-08T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-10T00:00:00+05:00 | 2026-02-09 12:00 | 2026-02-09T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-11T00:00:00+05:00 | 2026-02-10 12:00 | 2026-02-10T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-12T00:00:00+05:00 | 2026-02-11 12:00 | 2026-02-11T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-13T00:00:00+05:00 | 2026-02-12 12:00 | 2026-02-12T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-14T00:00:00+05:00 | 2026-02-13 12:00 | 2026-02-13T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-15T00:00:00+05:00 | 2026-02-14 12:00 | 2026-02-14T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-16T00:00:00+05:00 | 2026-02-15 12:00 | 2026-02-15T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-17T00:00:00+05:00 | 2026-02-16 12:00 | 2026-02-16T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-18T00:00:00+05:00 | 2026-02-17 12:00 | 2026-02-17T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-19T00:00:00+05:00 | 2026-02-18 12:00 | 2026-02-18T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-20T00:00:00+05:00 | 2026-02-19 12:00 | 2026-02-19T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-21T00:00:00+05:00 | 2026-02-20 12:00 | 2026-02-20T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-22T00:00:00+05:00 | 2026-02-21 12:00 | 2026-02-21T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-23T00:00:00+05:00 | 2026-02-22 12:00 | 2026-02-22T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-24T00:00:00+05:00 | 2026-02-23 12:00 | 2026-02-23T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-25T00:00:00+05:00 | 2026-02-24 12:00 | 2026-02-24T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-26T00:00:00+05:00 | 2026-02-25 12:00 | 2026-02-25T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-27T00:00:00+05:00 | 2026-02-26 12:00 | 2026-02-26T23:00:00+05:00 | 7–54 h | ok |
| 2026-02-28T00:00:00+05:00 | 2026-02-27 12:00 | 2026-02-27T23:00:00+05:00 | 7–54 h | ok |

## Files

- Forecasts: `data/weather/february_backtest.csv`
- Skipped blocks log: `data/weather/february_backtest_skipped.csv` (header only = nothing skipped)
