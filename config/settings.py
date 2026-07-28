"""ASTRA Configuration Settings"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "astra.duckdb"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

SIMULATION_CONFIG = {
    "default_satellite_count": 10,
    "default_readings_per_satellite": 500,
    "max_satellites": 5000,
    "orbit_period_minutes": 90,
    "sampling_interval_seconds": 10,
    "seed": 42,
}

VALIDATION_CONFIG = {
    "max_missing_pct": 10.0,
    "max_duplicate_pct": 5.0,
    "quality_threshold": 80.0,
    "battery_range": (0, 100),
    "temperature_range": (-50, 150),
    "altitude_range": (200, 2000),
    "velocity_range": (6.5, 8.5),
    "solar_voltage_range": (0, 50),
    "current_range": (0, 100),
    "cpu_range": (0, 100),
    "memory_range": (0, 100),
    "signal_range": (-120, 0),
    "radiation_range": (0, 1000),
    "gyro_range": (-500, 500),
    "accel_range": (-20, 20),
}

HEALTH_CONFIG = {
    "battery_weight": 25,
    "temperature_weight": 15,
    "signal_weight": 15,
    "solar_power_weight": 10,
    "cpu_weight": 10,
    "memory_weight": 10,
    "radiation_weight": 10,
    "sensor_status_weight": 5,
}

ANOMALY_CONFIG = {
    "contamination": 0.05,
    "n_estimators": 100,
    "random_state": 42,
    "temperature_spike_threshold": 3.0,
    "battery_drop_rate_threshold": -2.0,
    "signal_degradation_threshold": -15,
    "cpu_spike_threshold": 95,
    "memory_spike_threshold": 95,
}

VIZ_CONFIG = {
    "theme": "plotly_dark",
    "color_palette": ["#00CC96", "#EF553B", "#636EFA", "#AB63FA", "#FFA15A",
                       "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"],
    "width": 900,
    "height": 500,
    "export_format": "png",
}

API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "workers": 4,
}

DASHBOARD_CONFIG = {
    "page_title": "ASTRA - Satellite Telemetry Intelligence",
    "page_icon": "🛰️",
    "layout": "wide",
    "sidebar_state": "expanded",
}

LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "file": DATA_DIR / "astra.log",
}
