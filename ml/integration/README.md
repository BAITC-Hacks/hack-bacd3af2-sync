# Backend handoff

The existing `RealModelAdapter` imports `app.ml.predictor.predict_power`.
ML supplies that exact callable in `src.inference.predict`. No backend files
were modified. The backend owner can complete integration as follows:

1. Include the `ml/` directory and saved models in the backend runtime/container.
2. Install `ml/requirements-inference.txt` in the backend's environment. It
   matches backend's NumPy/Pandas/joblib pins. Keep the training environment
   (`ml/requirements.txt`) separate; do not install its conflicting pins into backend.
3. Add the absolute `ml/` directory to `PYTHONPATH`. Keep it present at worker start.
4. Copy this directory's `predictor.py` to `backend/app/ml/predictor.py`.
5. Set `MODEL_ADAPTER=real`. Optionally set `TURBINE_MODEL_DIR` to an absolute
   directory containing `turbine_1/` and `turbine_2/` model bundles.

No `features.py` copy or flat `models/turbine_1.cbm` layout is required: the ML
package owns feature building and bundle loading. Use the matching `.cbm` and
`metadata.json` together. The current bundles accept origins from February 1,
2026 at 00:00 Asia/Almaty onward. January 31 requires an earlier training cutoff.

## Contract

```python
from src.inference.predict import predict_power

forecast = predict_power(
    turbine_id=1,
    weather=weather_dataframe,
    horizon_hours=48,
    forecast_origin=origin,
)
```

Weather has `timestamp`, `wind_speed`, `temperature`, `forecast_origin`,
`latitude`, `longitude`. It must cover exactly 24 or 48 distinct consecutive
hours starting at origin. Shuffled rows are sorted; missing/extra hours, missing
values and different batch origins fail. Every row must describe the same site.
Naive clock times explicitly mean Asia/Almaty; aware times must use the named
Asia/Almaty timezone. Serialized fixed offsets are also accepted after checking
they match Asia/Almaty on each date (+05:00 for February 2026). Mismatched offsets
and other named zones are rejected rather than silently converted.

Output columns, in order: `forecast_origin`, `timestamp`, `turbine_id`,
`horizon_hour`, `wind_speed`, `temperature`, `predicted_power`, `model_version`.
Horizon 1 labels the interval `[origin, origin+1h)`. Output timestamps retain
local clock hours, matching the current backend's naive datetime convention.
`forecast.attrs['timezone']` explicitly records Asia/Almaty.

Input errors and model-origin violations raise `ValueError`. Missing/corrupt
artifacts raise `ModelArtifactError` (a `RuntimeError`). The backend owner should
map these into its existing API error handling. No silent mock fallback occurs
inside ML. Invalid/nonfinite predictions fail; clipping and low-wind/high-power
diagnostics are logged and retained in `forecast.attrs['diagnostics']`.
The CLI also saves these attrs in a `.diagnostics.json` sidecar.

Models are cached per process under a loading lock; repeated requests do not
reload or train. Restart workers or call `clear_model_cache()` after replacing
artifacts. Only trusted local model bundles may be loaded.

Backend owns archived weather provenance, forecast issue-time selection,
height selection and field mapping. Merely setting a `forecast_origin` column
cannot prove a weather run was available at that time. ML validates the shape,
timezone and origin consistency, but cannot verify issue time from this six-field
contract. Current offline training scores remain observed-weather proxy scores.

## CLI

From `ml/`, with the environment activated:

```text
python -m src.inference.predict --turbine 1 --weather data/weather/backend_batch.csv --horizon 48 --output data/predictions/turbine_1.csv
```

The batch is supplied by backend. There is no weather network client in ML.
