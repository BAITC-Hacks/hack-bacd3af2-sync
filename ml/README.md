# Wind turbine ML

Stages 1–3 implement ingestion, auditing, hourly aggregation, visual EDA,
chronological model selection and saved models for both turbines.
The supplied task requests staged delivery with an audit before model training.

## Setup and run

Python 3.11 or newer. From the repository root:

```powershell
py -m venv .venv
.venv/Scripts/python -m pip install -r ml/requirements.txt
cd ml
../.venv/Scripts/python -m src.data.audit --turbine-1 "C:/Users/User/Downloads/turbine 1.csv" --turbine-2 "C:/Users/User/Downloads/turbine 2.csv"
../.venv/Scripts/python -m src.data.preprocess --turbine-1 "C:/Users/User/Downloads/turbine 1.csv" --turbine-2 "C:/Users/User/Downloads/turbine 2.csv"
../.venv/Scripts/python -m src.analysis.eda
../.venv/Scripts/python -m src.training.train --turbine all
../.venv/Scripts/python -m unittest discover -s tests -v
```

On other platforms use `python3` and `.venv/bin/python`. Alternatively place the
two files in `ml/data/raw/` and omit the file arguments. Raw data is ignored by Git.
Paths are CLI parameters; defaults and diagnostic thresholds live in `src/config.py`.

Outputs:

- `reports/data_quality.json`: complete gaps, constant runs, missing values,
  parse errors, duplicates, physical range flags, spacing and monthly counts.
- `reports/data_quality.md`: human-readable summary and largest missing intervals.
- `data/processed/turbine_1_hourly.csv` and `turbine_2_hourly.csv`: complete hourly
  timelines with sensor aggregates, valid counts, eligibility and availability times.
- `reports/preprocessing.json`: accounting of exclusions and coverage.
- `reports/preprocessing_policy.md`: cleaning rules and feature availability.
- `reports/eda.md`, `reports/figures/`, `reports/power_curve.csv`: offline
  descriptive charts and binned power statistics. Processed data is ignored by Git
  and can be regenerated with the commands above.
- `models/turbine_1/` and `models/turbine_2/`: selected model artifacts,
  `metadata.json` and `metrics.json`. CatBoost uses native `.cbm` files.
- `reports/model_comparison.md`: selection and untouched holdout results.
- `reports/turbine_*_validation_predictions.csv.gz`: per-origin predictions
  and targets for independent metric checks.

Original CSVs are read only. UTF-8 headers are mapped explicitly, ID stays out
of numeric features, and invalid parsed values remain visible in audit counts.
SHA-256 fingerprints identify the input files. Output is deterministic for the
same input bytes and settings. Grid coverage includes missing boundary samples
within the configured study period. Source timestamps explicitly mean
`Asia/Almaty` (site approximately 43.64, 78.53), as configured in `src/config.py`.
Internal CSVs retain local wall-clock hours without silently converting to UTC.
Named-zone Asia/Almaty DataFrames are accepted with their clock hours preserved;
other aware zones are rejected. Naive input means Asia/Almaty, never machine time.
Kazakhstan's historical offset change makes some local times ambiguous: the
original wall-clock dataset does not distinguish repeated instances. No UTC
instant or extra observation is invented for those times.

## Delivery stages

1. **Complete:** input loading, automated data audit, reports and audit tests.
2. **Complete:** visual EDA, documented cleaning rules and hourly aggregation with coverage counts.
3. **Complete:** reusable features, chronological validation, persistence and power-curve baselines,
   candidate models, selection metrics and saved artifacts for each turbine.
4. Validated inference and backend integration, then historical forecast backtesting.

The planned backend API is
`predict_power(turbine_id, weather, horizon_hours, forecast_origin)`.
Weather input columns: `timestamp`, `wind_speed`, `temperature`,
`forecast_origin`, `latitude`, `longitude`. Output columns: `forecast_origin`,
`timestamp`, `turbine_id`, `horizon_hour`, `wind_speed`, `temperature`,
`predicted_power`, `model_version`. Only 24- and 48-hour horizons are intended.
This API is not implemented yet. Backend retrieves real archived forecasts from
Open-Meteo Previous Runs / Historical Forecast API and provides the standardized
columns above in Asia/Almaty, aligned to turbine hours. Wind-height selection,
mapping `wind_speed_100m/10m` to `wind_speed`, and mapping `temperature_2m` to
`temperature` belong to backend. ML does not request weather, parse heights or
rename provider fields. The weather contract is a production input, not a stub.

The local training run did not receive archived forecast batches or February labels. Future
observed weather cannot substitute for forecasts available at each historical
origin. The current scores use observed-weather proxies and do not establish
operational forecasting accuracy. Archived-weather evaluation and deployment
remain later stages.

## Training and leakage boundaries

Run `python -m src.training.train --turbine 1` or `--turbine 2` for an individual
model, or `--turbine all` to regenerate the combined report. Parameters and
feature sets are recorded in each artifact's metadata. CPU training uses four
threads and seed 42. Versions are pinned in requirements and recorded in metadata.

- Training input rejects **any target at or after 2026-02-01**, even an ineligible
  row. No February label file is opened. Synthetic February timestamps appear
  only in boundary tests.
- June, September and November 2025 are expanding-training selection windows.
  December 2025–January 2026 is evaluated only after selection is frozen.
- Every fold fits only rows with `available_at <= first_forecast_origin`.
  The models remain fixed within each window. Persistence baselines may consume
  newly available historical power at subsequent daily origins.
- HistGradientBoosting disables its automatic early-stopping split. CatBoost
  has fixed iterations and no evaluation-set tuning. No power lags are used.
- Calendar features use Asia/Almaty timestamps. ID, target, future variance
  and coverage counts are not predictors. Wind-only bin means are refit per fold.
- The final saved model is refit on the complete history through January 31.
  **It must not be used for an origin before its `training_last_available_at`**
  (February 1 at 00:00 for the supplied data). A January 31 historical origin
  requires a separate fit using only information available then.
- Reported holdout metrics belong to the fit ending November 30, not the final
  refit. Future observed weather is explicitly a proxy in these experiments;
  archived forecasts are necessary for an operational backtest.

Warm regional temperatures (including March nights around +15°C and January
around +1.4°C) are not anomalies. Temperature IQR flags are disabled, and finite
temperature values are not clipped or removed. Missing/nonfinite values remain
explicit data-quality issues.

Model code follows the [CatBoost regressor API](https://catboost.ai/docs/en/concepts/python-reference_catboostregressor)
and [HistGradientBoosting API](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html).
