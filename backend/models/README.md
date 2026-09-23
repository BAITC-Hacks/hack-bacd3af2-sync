Place trained model artifacts here (provided by the ML part):

- `turbine_1.cbm`, `turbine_2.cbm` — CatBoost models
- `metrics.json` — validation scores served by `GET /api/metrics`:
  `[{"turbine_id": 1, "mae": 0.08, "rmse": 0.12, "r2": 0.78}, ...]`
