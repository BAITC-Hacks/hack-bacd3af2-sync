import numpy as np
import pandas as pd
from src.time_utils import local_history


class EmpiricalPowerCurve:
    """Fixed-width wind bins fitted only on a fold's training history."""
    def __init__(self, bin_width=.5):
        self.bin_width = bin_width

    def fit(self, features, target):
        frame = pd.DataFrame({"wind": np.asarray(features["wind_speed"]), "power": np.asarray(target)})
        bins = np.floor(frame.wind / self.bin_width).astype(int)
        grouped = frame.groupby(bins).agg(wind=("wind", "mean"), power=("power", "mean"))
        self.wind = grouped.wind.to_numpy()
        self.power = grouped.power.to_numpy()
        return self

    def predict(self, features):
        return np.interp(features["wind_speed"], self.wind, self.power)


def historical_baselines(history, pairs):
    """Only readings with available_at <= origin may contribute.

    Seasonal repeats the prior 24h for both forecast days. Missing seasonal
    slots fall back to last-known power, with fallback and staleness recorded.
    """
    history, pairs = local_history(history), local_history(pairs)
    persistence = np.empty(len(pairs))
    seasonal = np.empty(len(pairs))
    fallback = np.zeros(len(pairs), dtype=bool)
    age = np.empty(len(pairs))
    for origin, indices in pairs.groupby("forecast_origin", sort=False).groups.items():
        past = history.loc[history.training_eligible & history.available_at.le(origin) & history.timestamp.lt(origin)]
        if past.empty:
            raise ValueError("Persistence has no historical observations")
        last = past.iloc[-1]
        persistence[indices] = last.power_mean
        age[indices] = (origin - last.available_at).total_seconds() / 3600
        offsets = (pairs.loc[indices, "timestamp"] - origin) % pd.Timedelta(days=1)
        source_times = origin - pd.Timedelta(days=1) + offsets
        values = past.set_index("timestamp").power_mean.reindex(source_times).to_numpy()
        missing = ~np.isfinite(values)
        seasonal[indices] = np.where(missing, last.power_mean, values)
        fallback[indices] = missing
    return {"persistence": persistence, "seasonal_persistence": seasonal}, {
        "seasonal_fallback_rows": int(fallback.sum()),
        "persistence_max_staleness_hours": float(age.max()),
        "persistence_stale_rows_over_24h": int((age > 24).sum()),
    }
