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

### Walk-forward baseline comparison

| Window | Model | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| selection_2025-06 | persistence | 0.270150 | 0.357438 | -0.487328 |
| selection_2025-06 | seasonal_persistence | 0.321086 | 0.413561 | -0.991057 |
| selection_2025-06 | power_curve | 0.042261 | 0.115721 | 0.844106 |
| selection_2025-06 | catboost_weather | 0.034065 | 0.109815 | 0.859614 |
| selection_2025-09 | persistence | 0.347841 | 0.447160 | -0.725111 |
| selection_2025-09 | seasonal_persistence | 0.385462 | 0.493532 | -1.101459 |
| selection_2025-09 | power_curve | 0.018280 | 0.032112 | 0.991104 |
| selection_2025-09 | catboost_weather | 0.014130 | 0.029812 | 0.992332 |
| selection_2025-11 | persistence | 0.352190 | 0.460554 | -0.510148 |
| selection_2025-11 | seasonal_persistence | 0.406285 | 0.521909 | -0.939309 |
| selection_2025-11 | power_curve | 0.023550 | 0.035524 | 0.991016 |
| selection_2025-11 | catboost_weather | 0.016231 | 0.031208 | 0.993066 |

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

### Walk-forward baseline comparison

| Window | Model | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| selection_2025-06 | persistence | 0.291806 | 0.389850 | -0.572631 |
| selection_2025-06 | seasonal_persistence | 0.345426 | 0.442104 | -1.022463 |
| selection_2025-06 | power_curve | 0.022008 | 0.032150 | 0.989305 |
| selection_2025-06 | catboost_weather | 0.014241 | 0.024256 | 0.993912 |
| selection_2025-09 | persistence | 0.345519 | 0.444992 | -0.709974 |
| selection_2025-09 | seasonal_persistence | 0.385480 | 0.492622 | -1.095623 |
| selection_2025-09 | power_curve | 0.015750 | 0.028474 | 0.992998 |
| selection_2025-09 | catboost_weather | 0.012664 | 0.026720 | 0.993834 |
| selection_2025-11 | persistence | 0.345111 | 0.456509 | -0.495535 |
| selection_2025-11 | seasonal_persistence | 0.396227 | 0.513103 | -0.889321 |
| selection_2025-11 | power_curve | 0.019232 | 0.028506 | 0.994168 |
| selection_2025-11 | catboost_weather | 0.014461 | 0.024612 | 0.995653 |

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

## Scope of these metrics

Saved artifacts passed prediction round-trip checks. Inference and real February archive replay are implemented separately; February accuracy still needs actual labels. Separate turbine fits beat the listed baselines here; a pooled turbine model has not been tested, so superiority over pooling is not established. See completion_status.md for delivery status.
