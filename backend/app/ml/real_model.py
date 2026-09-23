"""Adapter for the ML team's trained CatBoost models (ml/ package).

Default adapter (MODEL_ADAPTER=real). Install the inference stack first:
    pip install -r backend/requirements-ml.txt

Model selection by forecast_origin (anti-leakage)
-------------------------------------------------
Several model bundles exist, each trained on data up to a cutoff that metadata.json records
as `training_last_available_at` (the moment its last training hour was observable):

    ml/models/turbine_N/                    main models,   available from 2026-02-01 00:00
    ml/models/asof_2026-01-31/turbine_N/    early models,  available from 2026-01-31 00:00

Rule: for each request use the NEWEST bundle whose training data were fully available at
forecast_origin, i.e. `training_last_available_at <= forecast_origin`. So the main models
serve 2026-02-01 onward and the as-of snapshot serves 2026-01-31 — the main models were
trained on January 31 itself and would leak into that origin. An origin earlier than every
bundle is rejected. The ML loader enforces the same guard again as a second line of defence.

TURBINE_MODEL_DIR overrides the main bundle root; as-of snapshots are discovered in its
asof_*/ subdirectories.
"""

import asyncio
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.constants import TURBINES
from app.ml.model_adapter import ModelAdapter, ModelPredictionError, ModelUnavailableError

logger = logging.getLogger(__name__)

PredictWithModels = Callable[[int, pd.DataFrame, int, datetime, str], pd.DataFrame]


@dataclass(frozen=True, slots=True)
class ModelBundleInfo:
    turbine_id: int
    root: Path
    version: str
    available_at: pd.Timestamp


def _ensure_on_path(ml_package_dir: Path) -> None:
    if not (ml_package_dir / "src" / "inference" / "predict.py").is_file():
        raise ModelUnavailableError(
            f"ML package not found at {ml_package_dir} (expected src/inference/predict.py). "
            "Set ML_PACKAGE_DIR. (MODEL_ADAPTER=mock is for offline development only, not for the demo.)"
        )
    path = str(ml_package_dir.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)


def _bundle_roots(model_dir: Path) -> list[Path]:
    if not model_dir.is_dir():
        raise ModelUnavailableError(
            f"Model directory {model_dir} does not exist. Set TURBINE_MODEL_DIR. (MODEL_ADAPTER=mock is for offline development only, not for the demo.)"
        )
    return [model_dir, *sorted(path for path in model_dir.glob("asof_*") if path.is_dir())]


class RealModelAdapter(ModelAdapter):
    name = "CatBoost"

    def __init__(
        self,
        model_dir: Path,
        ml_package_dir: Path,
        turbine_ids: Sequence[int] = tuple(TURBINES),
    ) -> None:
        _ensure_on_path(ml_package_dir)
        try:
            from app.ml.predictor import ModelArtifactError, get_model, predict_with_models
        except ImportError as exc:
            raise ModelUnavailableError(
                f"Cannot import the ML inference package ({exc}). "
                "Install it with `pip install -r backend/requirements-ml.txt`. (MODEL_ADAPTER=mock is for offline development only.)"
            ) from exc

        self._predict_with_models: PredictWithModels = predict_with_models
        self._artifact_error: type[Exception] = ModelArtifactError
        self._bundles: dict[int, list[ModelBundleInfo]] = {turbine_id: [] for turbine_id in turbine_ids}

        # Validate every bundle once (SHA-256, feature schema, cutoff) so a broken artifact
        # stops the server at startup with a clear message instead of failing mid-demo.
        for root in _bundle_roots(model_dir):
            for turbine_id in turbine_ids:
                if not (root / f"turbine_{turbine_id}").is_dir():
                    if root == model_dir:
                        raise ModelUnavailableError(f"Main model bundle {root / f'turbine_{turbine_id}'} is missing.")
                    continue  # an as-of snapshot may cover only some turbines
                try:
                    bundle = get_model(turbine_id, str(root))
                except ModelArtifactError as exc:
                    raise ModelUnavailableError(str(exc)) from exc
                self._bundles[turbine_id].append(
                    ModelBundleInfo(turbine_id, root, bundle.version, pd.Timestamp(bundle.available_at))
                )

        for turbine_id, bundles in self._bundles.items():
            logger.info(
                "Turbine %d models: %s",
                turbine_id,
                ", ".join(f"{b.version} (from {b.available_at}, {b.root.name})" for b in bundles),
            )

    @property
    def bundles(self) -> dict[int, list[ModelBundleInfo]]:
        return self._bundles

    def select_bundle(self, turbine_id: int, forecast_origin: datetime) -> ModelBundleInfo:
        """Newest bundle whose training data were fully available at forecast_origin."""
        origin = pd.Timestamp(forecast_origin)
        eligible = [b for b in self._bundles.get(turbine_id, []) if b.available_at <= origin]
        if not eligible:
            earliest = min((b.available_at for b in self._bundles.get(turbine_id, [])), default=None)
            raise ModelPredictionError(
                f"No turbine {turbine_id} model was trained strictly before origin {origin}"
                + (f" (earliest bundle is usable from {earliest})." if earliest is not None else ".")
            )
        return max(eligible, key=lambda bundle: bundle.available_at)

    async def predict(
        self,
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame:
        bundle = self.select_bundle(turbine_id, forecast_origin)
        try:
            # CatBoost inference is CPU-bound and synchronous: keep the event loop free.
            return await asyncio.to_thread(
                self._predict_with_models, turbine_id, weather, horizon_hours, forecast_origin, str(bundle.root)
            )
        except (ValueError, self._artifact_error) as exc:
            raise ModelPredictionError(f"Turbine {turbine_id} ({bundle.version}): {exc}") from exc
