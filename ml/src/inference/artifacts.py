"""Load trusted local artifacts once per process; clear cache after deployment."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from threading import RLock
import pandas as pd
from src.config import TIMEZONE
from src.time_utils import local_timestamp
from src.training.models import load_model, feature_names, CANDIDATES


class ModelArtifactError(RuntimeError):
    """Missing, corrupted or incompatible model artifact."""


@dataclass(frozen=True)
class ModelBundle:
    model: object
    features: tuple[str, ...]
    version: str
    available_at: pd.Timestamp


_lock = RLock()


@lru_cache(maxsize=8)
def _load(turbine_id, root):
    folder = Path(root) / f"turbine_{turbine_id}"
    try:
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        name = metadata["model_type"]
        if name not in CANDIDATES or metadata["turbine_id"] != turbine_id or metadata["timezone"] != TIMEZONE:
            raise ValueError("Model identity or timezone mismatch")
        features = metadata["features"]
        if features != feature_names(name):
            raise ValueError("Model feature schema mismatch")
        filename = metadata["model_file"]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError("Model filename must stay inside its artifact directory")
        path = folder / filename
        if path.resolve().parent != folder.resolve():
            raise ValueError("Model artifact resolves outside its directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["artifact_sha256"]:
            raise ValueError("Model SHA-256 mismatch")
        available_at = local_timestamp(metadata["training_last_available_at"])
        end = local_timestamp(metadata["training_end"])
        if pd.isna(available_at) or pd.isna(end) or available_at < end + pd.Timedelta(hours=1):
            raise ValueError("Invalid model training availability metadata")
        version = metadata["model_version"]
        if not isinstance(version, str) or not version:
            raise ValueError("Missing model version")
        model = load_model(name, path)
        if name.startswith("catboost") and list(model.feature_names_) != features:
            raise ValueError("Native model features disagree with metadata")
        return ModelBundle(model, tuple(features), version, available_at)
    except Exception as exc:
        raise ModelArtifactError(f"Cannot load turbine {turbine_id} model: {exc}") from exc


def get_model(turbine_id, root):
    with _lock:
        return _load(int(turbine_id), str(Path(root).resolve()))


def clear_model_cache():
    """Call on artifact deployment, or restart the worker."""
    with _lock:
        _load.cache_clear()
