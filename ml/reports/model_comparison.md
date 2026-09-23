# Model comparison

## Scope

These are observed-weather proxy experiments, not operational weather-forecast backtests. All inputs and targets are before February 2026. February data is rejected, not silently filtered.

## Validation protocol

- Selection windows: June, September and November 2025, each trained only on complete hours available before its first origin. Models remain frozen within each window.
- Choose the lowest equally weighted mean window MAE among power curve, histogram boosting, CatBoost weather-only and CatBoost with calendar features. Fixed parameters; no random holdout or early-stopping split.
- Freeze the choice before checking December 2025 through January 2026. This holdout model trains only through November 30. Final saved models are then refit through January 31; their training fit is not the reported holdout score.
- Daily midnight origins have 48 hourly intervals entirely within each window. Horizon 1 labels [origin, origin+1h); the timestamp is the interval start. Origins too near the window end are excluded.
- Scores use common eligible target pairs. Overlapping target timestamps count separately for each origin; pair counts and unique target counts are retained in metrics.json. Missing hours keep their true lead times.
- Persistence uses last complete power available at origin. Seasonal persistence repeats the previous day's 24-hour profile across both days; missing slots use persistence, with fallback counts recorded.
- Model features use only wind, temperature and calendar transformations. No future observed within-hour statistics or power lags. Actual target-hour weather is an explicitly labeled proxy, not claimed to be available at origin.
- MAE and RMSE use normalized power units. Normalized MAE divides by rated normalized capacity 1. R² is unavailable for constant targets. No MAPE.

## Turbine 1

Selected **catboost_weather**, version `catboost_weather-65cc90032f20`. Final fit: 23,667 complete hours.

| Candidate | Mean selection MAE |
| --- | ---: |
| catboost_weather | 0.021475 |
| catboost_calendar | 0.021702 |
| hist_gradient_boosting | 0.021886 |
| power_curve | 0.028030 |

### Untouched holdout results

| Model | MAE | RMSE | R² | Pairs |
| --- | ---: | ---: | ---: | ---: |
| persistence | 0.352035 | 0.475009 | -0.686434 | 2920 |
| seasonal_persistence | 0.373868 | 0.489056 | -0.787656 | 2920 |
| power_curve | 0.034566 | 0.056440 | 0.976191 | 2920 |
| catboost_weather | 0.024389 | 0.052239 | 0.979604 | 2920 |

Holdout uses 61 origins and 1484 unique target hours. Seasonal fallback rows: 8; maximum persistence staleness: 0.0 hours.

Full per-window, per-horizon, wind-bin and clipping diagnostics: `../models/turbine_1/metrics.json`. Reproducible prediction pairs: `turbine_1_validation_predictions.csv.gz`.

## Turbine 2

Selected **catboost_weather**, version `catboost_weather-16a0619417f5`. Final fit: 24,785 complete hours.

| Candidate | Mean selection MAE |
| --- | ---: |
| catboost_weather | 0.013789 |
| catboost_calendar | 0.013846 |
| hist_gradient_boosting | 0.013877 |
| power_curve | 0.018997 |

### Untouched holdout results

| Model | MAE | RMSE | R² | Pairs |
| --- | ---: | ---: | ---: | ---: |
| persistence | 0.351315 | 0.474582 | -0.705607 | 2908 |
| seasonal_persistence | 0.372024 | 0.487851 | -0.802314 | 2908 |
| power_curve | 0.039945 | 0.083068 | 0.947746 | 2908 |
| catboost_weather | 0.028126 | 0.079774 | 0.951808 | 2908 |

Holdout uses 61 origins and 1478 unique target hours. Seasonal fallback rows: 18; maximum persistence staleness: 0.0 hours.

Full per-window, per-horizon, wind-bin and clipping diagnostics: `../models/turbine_2/metrics.json`. Reproducible prediction pairs: `turbine_2_validation_predictions.csv.gz`.

## Weather integration

History and backend weather use Asia/Almaty clock hours without UTC conversion. Backend supplies real archived Open-Meteo forecasts, already mapped to wind_speed and temperature. ML does not fetch weather or interpret wind-height fields. Existing scores still use observed-weather proxies; archived forecasts have not been evaluated in this training run.

## Remaining work

Saved artifacts passed prediction round-trip checks. Backend predict_power input validation, model caching and archived-weather backtesting remain a separate stage. Separate turbine fits are compared with baselines here; a pooled turbine model has not been tested, so superiority over pooling is not established.
