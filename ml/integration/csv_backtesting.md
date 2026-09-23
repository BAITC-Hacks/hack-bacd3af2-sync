# February backtest from the backend CSV

ML reads only the repository file `data/weather/february_backtest.csv`.
It performs no API requests, wind-height selection or provider-field mapping.
Required columns, with no actual-power fields:

```text
forecast_origin,timestamp,turbine_id,wind_speed,temperature,latitude,longitude,weather_valid_time,weather_source
```

All clock times mean **Asia/Almaty**, without silent UTC conversion.
For this backend export, `weather_valid_time` means **run availability**, defined
as `run_init + 6 hours`, not target validity time. The runner parses the explicit
UTC `run=` timestamp in `weather_source`, explicitly converts that run metadata
to Asia/Almaty, and checks `run_init + 6h == weather_valid_time <= forecast_origin`.
Provider provenance and the six-hour publication-delay bound come from the
backend export report; ML performs no network verification. The CSV's +05:00
offsets are checked against Asia/Almaty and local target hours are preserved.

## Run

From `ml/` with requirements installed:

```text
python -m src.backtesting.run --output-dir data/backtests/february
```

Default input resolves relative to the repository root regardless of working
directory. Explicit input from `ml/` is equivalent:

```text
python -m src.backtesting.run --weather ../data/weather/february_backtest.csv --output-dir data/backtests/february
```

Both turbines are required for all 29 daily midnight origins from January 31 to
February 28 inclusive: 58 batches. Each batch must contain 48 distinct consecutive
hours. The runner sorts and validates all batches before predicting both windows:
first 24 rows and all 48 rows. Missing hours, duplicates, extra origins and actual
power columns fail. No interpolation, training or actual-label loading occurs.
Output must be a new directory. Partial runs require explicit `--start` and `--end`.

The existing backend interval convention is retained: `timestamp == origin`
labels `[origin, origin+1h)`. A February 28 48h batch ends March 1 at 23:00.
January 31 includes January targets; evaluation restricts targets to February.

## Saved results

Both `24h/predictions.csv` and `48h/predictions.csv` have exactly:

```text
forecast_origin,target_timestamp,horizon_hours,turbine_id,predicted_power,wind_speed_forecast,temperature_forecast,model_version
```

The complete run produces 1,392 rows for 24h and 2,784 for 48h.
`horizon_hours` is the **one-based lead hour**, 1–24 or 1–48, matching inference's
`horizon_hour`. Window length is identified by the folder and
`forecast_window_hours` in its `run.json`. Each metadata file also stores input
and output hashes, source, timezone, model versions and prediction diagnostics.

This field indexes the power forecast intervals from origin. It is **not NWP
weather lead time**: weather lead is computed as `timestamp - run_init` from
`weather_source`, recorded per batch in `run.json`, and is 7–30h / 7–54h for this
export. Selected CatBoost models use only wind and temperature, not lead time.
Both turbines share the same Open-Meteo grid weather; this is accepted. Their
separate models provide turbine-specific power predictions.

Keys are `(forecast_origin, target_timestamp, turbine_id)` within each file.
Multiple forecasts of the same target from different origins are retained.

## Model cutoff and leakage

- **January 31 00:00** uses `models/asof_2026-01-31/turbine_{1,2}/`, trained
  through **January 30 23:00**, available at January 31 midnight. No January 31
  training rows are used.
- **February 1–28** uses `models/turbine_{1,2}/`, trained through January 31
  23:00 and available at February 1 midnight. No February observations are used.
- Every call checks `forecast_origin >= training_last_available_at`. Final
  models supplied for January 31 fail explicitly; no leakage bypass exists.
- Selected models use forecast wind and temperature, not actual power, future
  observed variance or power lags. Selection is frozen from pre-holdout 2025
  windows; no February tuning occurs.

To reproduce early models in a new directory:

```text
python -m src.backtesting.prepare_snapshot --cutoff "2026-01-31 00:00:00" --output-dir models/reproduced_asof_2026-01-31
```

`--early-model-dir` and `--model-dir` override artifact directories during replay.

## Separate evaluation only after actuals arrive

Provide a separate CSV containing exactly `timestamp,turbine_id,power_mean`:
complete hourly actual observations in the same local interval convention.
Do not fill missing labels with zero. After forecasts have been saved:

```text
python -m src.backtesting.evaluate --run-dir data/backtests/february/24h --actuals data/actuals/february_hourly.csv --output data/backtests/february/24h/evaluation.json
python -m src.backtesting.evaluate --run-dir data/backtests/february/48h --actuals data/actuals/february_hourly.csv --output data/backtests/february/48h/evaluation.json
```

Evaluation never predicts or trains. It verifies the frozen prediction hash,
joins actuals many-to-one and filters target times to `[2026-02-01, 2026-03-01)`.
MAE/RMSE/R², normalized MAE and breakdowns by lead hour and wind bin are reported
per turbine, separately for each window. Missing labels and out-of-month targets
are counted. Duplicate actual labels fail; unmatched turbines have null metrics.
No matched labels means no score. Overlapping origins retain equal pair weight.

## Status

The real backend CSV has been imported and replayed for all 29 origins. Results
are in `ml/reports/february_backtest/{24h,48h}/`. Forecast generation is complete;
accuracy metrics still require actual February power labels. Synthetic tests
remain separate from the real outputs. The older `--manifest` mode
remains available but is not required here. CSV mode always runs both horizons;
do not pass the manifest-only `--horizon` argument.
