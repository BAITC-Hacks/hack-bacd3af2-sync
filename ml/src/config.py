"""Shared defaults; timestamps remain source-local until timezone is confirmed."""
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ML_ROOT / "data" / "raw"
REPORT_DIR = ML_ROOT / "reports"
EXPECTED_START = "2023-03-11 00:00:00"
EXPECTED_END = "2026-01-31 23:50:00"
CADENCE_MINUTES = 10
CONSTANT_MIN_OBSERVATIONS = 36  # Six hours of samples at the expected cadence.
IQR_MULTIPLIER = 3.0
RANDOM_SEED = 42
