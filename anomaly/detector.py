"""ASTRA AI Anomaly Detection Engine"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import ANOMALY_CONFIG
from utils.helpers import setup_logging

logger = setup_logging("astra.anomaly")

ANOMALY_FEATURES = [
    "battery_pct", "temperature_c", "solar_voltage_v", "current_a",
    "cpu_usage_pct", "memory_usage_pct", "signal_strength_dbm",
    "radiation_level", "gyro_x", "gyro_y", "gyro_z",
    "accel_x", "accel_y", "accel_z",
]


class AnomalyDetector:
    def __init__(self):
        self.contamination = ANOMALY_CONFIG["contamination"]
        self.n_estimators = ANOMALY_CONFIG["n_estimators"]
        self.random_state = ANOMALY_CONFIG["random_state"]
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self._fitted = False

    def fit_detect(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"Running anomaly detection on {len(df)} records")

        features = [c for c in ANOMALY_FEATURES if c in df.columns]
        if len(features) < 2:
            logger.warning("Not enough features for anomaly detection")
            df_out = df.copy()
            df_out["anomaly_score"] = 1
            df_out["is_anomaly"] = False
            df_out["anomaly_type"] = "none"
            return df_out

        X = df[features].copy()
        X = X.fillna(X.median())

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )

        predictions = self.model.fit_predict(X_scaled)
        scores = self.model.decision_function(X_scaled)

        df_out = df.copy()
        df_out["anomaly_score"] = scores
        df_out["is_anomaly"] = predictions == -1
        df_out["anomaly_type"] = "none"

        self._fitted = True

        anomaly_count = df_out["is_anomaly"].sum()
        logger.info(f"Detected {anomaly_count} anomalies ({anomaly_count/len(df_out)*100:.2f}%)")
        return df_out

    def detect_statistical(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        logger.info("Running statistical threshold detection")
        anomalies = []

        _anomaly_check(df, "temperature_c", "temperature_spike",
                        lambda s: s > s.rolling(20).mean() + ANOMALY_CONFIG["temperature_spike_threshold"] * s.std(),
                        anomalies, "C")

        _anomaly_check(df, "battery_pct", "battery_drop",
                        lambda s: s.diff() < ANOMALY_CONFIG["battery_drop_rate_threshold"],
                        anomalies, "%")

        _anomaly_check(df, "signal_strength_dbm", "signal_loss",
                        lambda s: s < s.rolling(20).mean() + ANOMALY_CONFIG["signal_degradation_threshold"],
                        anomalies, "dBm")

        _anomaly_check(df, "cpu_usage_pct", "cpu_overload",
                        lambda s: s > ANOMALY_CONFIG["cpu_spike_threshold"],
                        anomalies, "%")

        _anomaly_check(df, "memory_usage_pct", "memory_overload",
                        lambda s: s > ANOMALY_CONFIG["memory_spike_threshold"],
                        anomalies, "%")

        logger.info(f"Statistical detection found {len(anomalies)} anomaly events")
        return anomalies

    def classify_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if not self._fitted or self.model is None:
            logger.warning("Model not fitted, running fit_detect first")
            df = self.fit_detect(df)

        classified = self.detect_statistical(df)

        anomaly_df = df[df["is_anomaly"] == True]
        if len(anomaly_df) > 0 and len(classified) == 0:
            logger.info(f"No statistical anomalies found but {len(anomaly_df)} ML anomalies exist")

        return classified

    def get_anomaly_summary(self, df: pd.DataFrame, satellite_id: str) -> Dict[str, Any]:
        sat_df = df[df["satellite_id"] == satellite_id].copy()
        if "anomaly_score" not in sat_df.columns:
            sat_df = self.fit_detect(sat_df)

        anomalies = self.detect_statistical(sat_df)

        return {
            "satellite_id": satellite_id,
            "timestamp": datetime.utcnow().isoformat(),
            "total_anomalies": len(anomalies),
            "anomalies": anomalies,
            "ml_anomaly_pct": round(float(sat_df["is_anomaly"].mean() * 100), 2),
            "severity": _severity_from_count(len(anomalies)),
            "summary": _summarize_anomalies(anomalies),
        }


def _anomaly_check(df, col, atype, condition, results, unit):
    if col not in df.columns:
        return
    mask = condition(df[col])
    indices = df.index[mask].tolist()
    if not indices:
        return
    for idx in indices:
        results.append({
            "type": atype,
            "timestamp": df.loc[idx, "timestamp"].isoformat() if "timestamp" in df.columns else str(idx),
            "metric": col,
            "value": float(df.loc[idx, col]),
            "unit": unit,
            "severity": "High" if abs(df.loc[idx, col]) > df[col].std() * 3 else "Medium",
        })


def _severity_from_count(count: int) -> str:
    if count > 20:
        return "Critical"
    elif count > 10:
        return "High"
    elif count > 5:
        return "Medium"
    return "Low"


def _summarize_anomalies(anomalies: List[Dict]) -> str:
    if not anomalies:
        return "No anomalies detected."
    types = {}
    for a in anomalies:
        types[a["type"]] = types.get(a["type"], 0) + 1

    parts = []
    type_labels = {
        "temperature_spike": "temperature spikes",
        "battery_drop": "rapid battery drops",
        "signal_loss": "signal degradation events",
        "cpu_overload": "CPU overload events",
        "memory_overload": "memory overload events",
    }
    for t, count in types.items():
        parts.append(f"{count} {type_labels.get(t, t)}")
    return "Detected: " + ", ".join(parts) + "."
