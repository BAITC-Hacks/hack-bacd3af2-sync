"""Shared defaults. All dataset and weather clock times refer to Asia/Almaty."""
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
TIMEZONE = "Asia/Almaty"
SITE_LATITUDE = 43.64
SITE_LONGITUDE = 78.53
WEATHER_PROVIDER = "backend: Open-Meteo Single Runs API archive export"
WEATHER_COLUMNS = ("timestamp", "wind_speed", "temperature", "forecast_origin", "latitude", "longitude")
LOW_WIND_SANITY_MPS = 1.0
HIGH_POWER_AT_LOW_WIND = 0.2  # Diagnostic only; never a clipping/deletion rule.
# Regional warmth is not evidence of a sensor anomaly. No temperature IQR flags.
IQR_DIAGNOSTIC_COLUMNS = ("wind_speed", "power")
RAW_DIR = ML_ROOT / "data" / "raw"
PROCESSED_DIR = ML_ROOT / "data" / "processed"
REPORT_DIR = ML_ROOT / "reports"
EXPECTED_START = "2023-03-11 00:00:00"
EXPECTED_END = "2026-01-31 23:50:00"
CADENCE_MINUTES = 10
CONSTANT_MIN_OBSERVATIONS = 36  # Six hours of samples at the expected cadence.
IQR_MULTIPLIER = 3.0
RANDOM_SEED = 42
MODEL_DIR = ML_ROOT / "models"
TRAINING_CUTOFF = "2026-02-01 00:00:00"  # Exclusive target timestamp boundary.
SELECTION_WINDOWS = (
    ("2025-06-01", "2025-07-01"),
    ("2025-09-01", "2025-10-01"),
    ("2025-11-01", "2025-12-01"),
)
HOLDOUT_WINDOW = ("2025-12-01", TRAINING_CUTOFF)
