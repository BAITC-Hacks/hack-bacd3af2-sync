# ML delivery status

## Implemented and verified

| Requirement | Evidence |
| --- | --- |
| Automated audit, gaps, duplicates, invalid values | data_quality.md / .json and audit tests |
| Visual EDA and physical power curve | eda.md, figures/, power_curve.csv |
| Hourly aggregation and explicit cleaning policy | preprocessing_policy.md, counts and availability timestamps |
| Forecast-reproducible features; no target leakage | features/build_features.py and leakage tests |
| Chronological walk-forward and December–January holdout | model_comparison.md; per-turbine metrics.json |
| Persistence, seasonal persistence and empirical curve comparison | Walk-forward and holdout tables in model_comparison.md |
| Candidate selection and separate turbine models | CatBoost weather-only selected before holdout; native artifacts and hashes |
| MAE/RMSE/R², lead-hour and wind-bin metrics | metrics.json and saved validation prediction pairs |
| As-of model for January 31 | models/asof_2026-01-31, trained only through January 30 |
| Backend Python contract, cached loading, physical output checks | inference/, weather/schema.py, integration handoff |
| CLI and real February archived-weather replay | february_backtest/24h and 48h, provenance and forecast hashes |
| Separate post-prediction evaluation | backtesting/evaluate.py; labels never enter inference or fitting |
| Explicit Asia/Almaty, archive availability and true NWP lead | timezone tests; run_init + 6h checks; lead 7–54h |

All mandatory ML functions can run on the supplied inputs. February forecasts
are saved, but forecast generation alone does not establish February accuracy.

## Still dependent on other inputs or owners

1. Actual February hourly power is absent. Once supplied, run the separate
   evaluator for both windows to obtain genuine archived-weather MAE/RMSE/R².
2. Backend owner must install the inference dependencies and apply the supplied
   predictor handoff in their directory/container. ML does not modify backend
   or frontend. The integration verifier exercises that seam in memory.

## Deliberate scope choices

- Production models omit power lags because the agreed weather-only contract
  supplies no recent turbine power. Persistence baselines still use only past
  power during historical validation. No recursive future-power substitution.
- Calendar features were compared and did not beat weather-only CatBoost.
- HistGradientBoosting was compared. LightGBM/XGBoost and neural networks are
  optional, not prerequisites for this implementation.
- Separate turbine models are delivered. A pooled-model experiment remains
  optional; this project does not claim separate models outperform pooling.
- Native CatBoost feature importance is stored in each model's metadata.
  Importance describes the fitted model, not causation.

Training and inference use separate dependency pins because backend already
pins older NumPy/Pandas/joblib. This avoids changing another team's environment.
The actual `RealModelAdapter` and backend output validator were exercised in
memory for both turbines at 24/48 hours using Pandas 2.2.3 and NumPy 2.2.5;
predictions matched the saved real archived-weather replay to 1e-12 tolerance.
