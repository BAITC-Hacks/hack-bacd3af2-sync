import numpy as np
import pandas as pd


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if len(actual) == 0 or actual.shape != predicted.shape or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Metrics require matching finite nonempty arrays")
    error = actual - predicted
    sst = float(np.sum((actual - actual.mean()) ** 2))
    mae = float(np.abs(error).mean())
    return {"n": len(actual), "mae": mae, "rmse": float(np.sqrt(np.mean(error ** 2))),
            "r2": 1 - float(np.sum(error ** 2)) / sst if sst > 0 else None,
            "normalized_mae": mae}  # Rated normalized capacity is 1.


def detailed_metrics(pairs, predicted):
    frame = pairs[["power_mean", "horizon_hour", "wind_speed_mean"]].copy()
    frame["predicted"] = predicted
    frame["wind_bin"] = pd.cut(frame.wind_speed_mean, [0, 3, 6, 9, 12, np.inf],
                                right=False, labels=["0-3", "3-6", "6-9", "9-12", "12+"])
    return {"overall": metrics(frame.power_mean, frame.predicted),
            "by_horizon": {str(int(h)): metrics(g.power_mean, g.predicted) for h, g in frame.groupby("horizon_hour")},
            "by_wind_bin": {str(b): metrics(g.power_mean, g.predicted) for b, g in frame.groupby("wind_bin", observed=True)}}
