"""Backend-owned handoff (copied from ml/integration/predictor.py).

The ML package lives in the repository's ml/ directory; RealModelAdapter puts it on
sys.path before importing this module. Inference dependencies: ml/requirements-inference.txt
(installed via backend/requirements-ml.txt).

Besides the contract function predict_power, the backend re-exports:
- predict_with_models: the same inference with an explicit model directory, so the
  adapter can pick a bundle per forecast_origin without mutating TURBINE_MODEL_DIR;
- get_model / ModelArtifactError: to validate every bundle (SHA-256, features,
  training cutoff) once at startup and fail fast with a clear error.
"""
from src.inference.artifacts import ModelArtifactError, get_model
from src.inference.predict import predict_power, predict_with_models

__all__ = ["ModelArtifactError", "get_model", "predict_power", "predict_with_models"]
