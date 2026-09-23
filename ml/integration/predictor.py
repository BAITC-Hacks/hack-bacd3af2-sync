"""Backend-owned handoff: copy to backend/app/ml/predictor.py after team review.

Make the repository's ml/ directory available on PYTHONPATH in the backend
environment and container, and install ml/requirements.txt. The repository's
backend and frontend directories are intentionally not changed by ML work.
"""
from src.inference.predict import predict_power

__all__ = ["predict_power"]
