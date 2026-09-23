import json
from pathlib import Path
import numpy as np
from src.config import RANDOM_SEED
from src.features.build_features import FEATURES, WEATHER_FEATURES
from src.training.baselines import EmpiricalPowerCurve

CANDIDATES = ("power_curve", "hist_gradient_boosting", "catboost_weather", "catboost_calendar")


def feature_names(name):
    return WEATHER_FEATURES if name in ("power_curve", "catboost_weather") else FEATURES


def parameters(name):
    if name == "power_curve":
        return {"bin_width": .5}
    if name == "hist_gradient_boosting":
        return {"loss": "absolute_error", "max_iter": 250, "learning_rate": .06,
                "max_leaf_nodes": 15, "l2_regularization": 2., "early_stopping": False,
                "random_state": RANDOM_SEED}
    if name in ("catboost_weather", "catboost_calendar"):
        return {"iterations": 500, "depth": 6, "learning_rate": .05, "loss_function": "MAE",
                "l2_leaf_reg": 5, "random_seed": RANDOM_SEED, "thread_count": 4,
                "allow_writing_files": False, "verbose": False}
    raise ValueError(f"Unknown candidate: {name}")


def create_model(name):
    from catboost import CatBoostRegressor
    from sklearn.ensemble import HistGradientBoostingRegressor
    cls = EmpiricalPowerCurve if name == "power_curve" else (
        HistGradientBoostingRegressor if name == "hist_gradient_boosting" else CatBoostRegressor)
    return cls(**parameters(name))


def checked_prediction(model, features):
    raw = np.asarray(model.predict(features), dtype=float)
    if raw.ndim != 1 or len(raw) != len(features) or not np.isfinite(raw).all():
        raise ValueError("Invalid model prediction shape or nonfinite values")
    return np.clip(raw, 0, 1), {"clipped_below_zero": int((raw < 0).sum()),
                              "clipped_above_one": int((raw > 1).sum())}


def save_model(model, name, folder: Path):
    if name.startswith("catboost"):
        path = folder / "model.cbm"
        model.save_model(str(path))
    elif name == "power_curve":
        path = folder / "model.json"
        path.write_text(json.dumps({"wind": model.wind.tolist(), "power": model.power.tolist(),
                                    "bin_width": model.bin_width}), encoding="utf-8")
    else:
        import joblib
        path = folder / "model.joblib"
        joblib.dump(model, path)
    return path


def load_model(name, path):
    """Load only trusted locally generated artifacts; joblib is not safe for untrusted files."""
    if name.startswith("catboost"):
        from catboost import CatBoostRegressor
        model = CatBoostRegressor()
        model.load_model(str(path))
        return model
    if name == "power_curve":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        model = EmpiricalPowerCurve(data["bin_width"])
        model.wind, model.power = np.array(data["wind"]), np.array(data["power"])
        return model
    if name == "hist_gradient_boosting":
        import joblib
        return joblib.load(path)
    raise ValueError(f"Unknown model type: {name}")
