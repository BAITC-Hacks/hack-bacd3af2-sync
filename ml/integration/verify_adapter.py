"""Verify the actual backend adapter in memory without editing backend files."""
import asyncio
import importlib.util
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "backend"))


async def verify():
    # Inject the provided handoff at the backend import seam, in this process only.
    import app.ml
    spec = importlib.util.spec_from_file_location("app.ml.predictor", Path(__file__).with_name("predictor.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    from app.ml.real_model import RealModelAdapter
    from app.utils.validation import validate_prediction_frame
    from src.time_utils import local_timestamps
    from src.config import WEATHER_COLUMNS
    weather = pd.read_csv(ROOT / "data/weather/february_backtest.csv")
    weather["forecast_origin"] = local_timestamps(weather.forecast_origin)
    weather["timestamp"] = local_timestamps(weather.timestamp)
    adapter = RealModelAdapter()
    count = 0
    for turbine in (1, 2):
        batch = weather.loc[weather.turbine_id.eq(turbine) & weather.forecast_origin.eq("2026-02-01")].sort_values("timestamp")
        for horizon in (24, 48):
            result = await adapter.predict(turbine, batch[list(WEATHER_COLUMNS)].iloc[:horizon], horizon, pd.Timestamp("2026-02-01").to_pydatetime())
            report = validate_prediction_frame(result, horizon)
            assert report.is_valid and not report.warnings, report.issues
            saved = pd.read_csv(ROOT / f"ml/reports/february_backtest/{horizon}h/predictions.csv")
            expected = saved.loc[saved.turbine_id.eq(turbine) & saved.forecast_origin.str.startswith("2026-02-01")]
            np.testing.assert_allclose(result.predicted_power, expected.predicted_power, atol=1e-12, rtol=1e-12)
            count += 1
    print(f"Backend RealModelAdapter and output validator passed {count} cases; predictions match saved real replay.")
    print(f"Runtime: pandas={pd.__version__}, numpy={np.__version__}")


if __name__ == "__main__":
    asyncio.run(verify())
