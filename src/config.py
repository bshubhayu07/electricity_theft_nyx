"""
System Configuration & Settings Module.

Centralizes paths, environment variables, model default parameters,
and threat detection thresholds across backend services.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

# Default File Paths
DATA_PATH = DATA_DIR / "smart_meter_readings.csv"
MODEL_PATH = MODELS_DIR / "theft_ensemble.joblib"
FEATURE_TABLE_PATH = MODELS_DIR / "feature_table.csv"

# Model Parameters
DEFAULT_FLAG_THRESHOLD = 0.50
SUPERVISED_WEIGHT = 0.65
ANOMALY_WEIGHT = 0.35

# API Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
API_TITLE = "Electricity Theft & Anomaly Detection API"
API_VERSION = "2.4.0-enterprise"
