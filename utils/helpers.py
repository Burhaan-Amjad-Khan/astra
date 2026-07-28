"""ASTRA Utility Helpers"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config.settings import LOG_CONFIG


def setup_logging(name: str = "astra") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_CONFIG["level"], logging.INFO))

    if not logger.handlers:
        fmt = logging.Formatter(LOG_CONFIG["format"])
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        logger.addHandler(console)

        log_file = Path(LOG_CONFIG["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def format_bytes(size: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def timestamp_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    try:
        return a / b if b != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def health_category(score: float) -> Dict[str, Any]:
    if score >= 90:
        return {"category": "Excellent", "color": "#00CC96", "emoji": "🟢"}
    elif score >= 70:
        return {"category": "Good", "color": "#636EFA", "emoji": "🔵"}
    elif score >= 40:
        return {"category": "Warning", "color": "#FFA15A", "emoji": "🟠"}
    else:
        return {"category": "Critical", "color": "#EF553B", "emoji": "🔴"}
