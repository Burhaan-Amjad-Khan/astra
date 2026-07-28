"""ASTRA Satellite Health Scoring Engine"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import HEALTH_CONFIG
from utils.helpers import setup_logging, health_category, clamp

logger = setup_logging("astra.health")


class HealthScorer:
    def __init__(self):
        self.weights = HEALTH_CONFIG
        self.metric_scorers = {
            "battery_pct": self._score_battery,
            "temperature_c": self._score_temperature,
            "signal_strength_dbm": self._score_signal,
            "solar_voltage_v": self._score_solar_power,
            "cpu_usage_pct": self._score_cpu,
            "memory_usage_pct": self._score_memory,
            "radiation_level": self._score_radiation,
            "sensor_status": self._score_sensor,
        }

    def compute_health(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info(f"Computing health scores for satellite data with {len(df)} records")
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_score": 0.0,
            "metric_scores": {},
            "status": "",
            "category": "",
            "recommendations": [],
        }

        scores = {}
        for metric, scorer in self.metric_scorers.items():
            if metric in df.columns:
                scores[metric] = scorer(df[metric])
                result["metric_scores"][metric] = scores[metric]

        overall = 0.0
        total_weight = 0.0
        for metric, weight_key in [
            ("battery_pct", "battery_weight"),
            ("temperature_c", "temperature_weight"),
            ("signal_strength_dbm", "signal_weight"),
            ("solar_voltage_v", "solar_power_weight"),
            ("cpu_usage_pct", "cpu_weight"),
            ("memory_usage_pct", "memory_weight"),
            ("radiation_level", "radiation_weight"),
            ("sensor_status", "sensor_status_weight"),
        ]:
            if metric in scores:
                w = self.weights[weight_key]
                overall += scores[metric]["score"] * w / 100
                total_weight += w

        if total_weight > 0:
            overall = (overall / total_weight) * 100
        else:
            overall = 50.0

        overall = round(clamp(overall, 0, 100), 1)
        hc = health_category(overall)

        result["overall_score"] = overall
        result["status"] = hc["category"]
        result["category"] = hc["category"]
        result["color"] = hc["color"]

        result["recommendations"] = self._generate_recommendations(scores)
        return result

    def _score_battery(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val >= 85:
            score = 95 + (mean_val - 85) * 0.33
        elif mean_val >= 60:
            score = 70 + (mean_val - 60) * 1.0
        elif mean_val >= 30:
            score = 40 + (mean_val - 30) * 1.0
        else:
            score = mean_val * 1.33
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "%",
            "status": "Healthy" if mean_val >= 70 else "Degraded" if mean_val >= 40 else "Critical",
        }

    def _score_temperature(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if 15 <= mean_val <= 35:
            score = 100 - abs(mean_val - 25) * 4
        elif 35 < mean_val <= 60:
            score = 60 - (mean_val - 35) * 1.6
        elif -20 <= mean_val < 15:
            score = 60 - (15 - mean_val) * 1.14
        else:
            score = max(0, 20 - abs(mean_val - 25) * 0.5)
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "C",
            "status": "Normal" if 15 <= mean_val <= 35 else "Elevated" if mean_val > 35 else "Cold",
        }

    def _score_signal(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val >= -50:
            score = 95 + (mean_val + 50) * 0.1
        elif mean_val >= -80:
            score = 70 + (mean_val + 80) * 0.83
        elif mean_val >= -100:
            score = 40 + (mean_val + 100) * 1.5
        else:
            score = max(0, 40 + (mean_val + 100) * 2)
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "dBm",
            "status": "Strong" if mean_val >= -60 else "Moderate" if mean_val >= -90 else "Weak",
        }

    def _score_solar_power(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val >= 28:
            score = 90 + (mean_val - 28) * 0.45
        elif mean_val >= 20:
            score = 60 + (mean_val - 20) * 3.75
        elif mean_val >= 10:
            score = 30 + (mean_val - 10) * 3
        else:
            score = mean_val * 3
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "V",
            "status": "Optimal" if mean_val >= 28 else "Adequate" if mean_val >= 20 else "Low",
        }

    def _score_cpu(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val <= 50:
            score = 95
        elif mean_val <= 75:
            score = 95 - (mean_val - 50) * 1.2
        elif mean_val <= 90:
            score = 65 - (mean_val - 75) * 2.33
        else:
            score = max(0, 30 - (mean_val - 90) * 3)
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "%",
            "status": "Normal" if mean_val <= 60 else "High" if mean_val <= 85 else "Critical",
        }

    def _score_memory(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val <= 60:
            score = 95
        elif mean_val <= 80:
            score = 95 - (mean_val - 60) * 1.75
        elif mean_val <= 95:
            score = 60 - (mean_val - 80) * 4
        else:
            score = max(0, 10 - (mean_val - 95))
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "%",
            "status": "Normal" if mean_val <= 65 else "High" if mean_val <= 88 else "Critical",
        }

    def _score_radiation(self, series: pd.Series) -> Dict:
        mean_val = float(series.mean())
        if mean_val <= 50:
            score = 95 + (30 - mean_val) * 0.1
        elif mean_val <= 150:
            score = 90 - (mean_val - 50) * 0.3
        elif mean_val <= 500:
            score = 60 - (mean_val - 150) * 0.1
        else:
            score = max(0, 25 - (mean_val - 500) * 0.05)
        return {
            "value": round(mean_val, 1),
            "score": round(clamp(score, 0, 100), 1),
            "unit": "rad",
            "status": "Low" if mean_val <= 100 else "Moderate" if mean_val <= 300 else "High",
        }

    def _score_sensor(self, series: pd.Series) -> Dict:
        healthy_pct = float((series == 1).mean() * 100)
        score = healthy_pct
        return {
            "value": round(healthy_pct, 1),
            "score": round(score, 1),
            "unit": "%",
            "status": "All Active" if healthy_pct > 98 else "Degraded" if healthy_pct > 80 else "Failed",
        }

    def _generate_recommendations(self, scores: Dict) -> List[str]:
        recommendations = []

        battery = scores.get("battery_pct", {})
        if battery.get("score", 100) < 50:
            recommendations.append("Critical: Battery levels are low. Consider power-saving mode and reducing non-essential operations.")
        elif battery.get("score", 100) < 70:
            recommendations.append("Warning: Battery degradation detected. Monitor charging cycles closely.")

        temp = scores.get("temperature_c", {})
        if temp.get("score", 100) < 50:
            recommendations.append("Critical: Temperature out of safe range. Check thermal control systems immediately.")
        elif temp.get("score", 100) < 70:
            recommendations.append("Warning: Temperature trending outside optimal range. Review thermal management.")

        signal = scores.get("signal_strength_dbm", {})
        if signal.get("score", 100) < 50:
            recommendations.append("Critical: Signal strength is weak. Check antenna alignment and communication systems.")
        elif signal.get("score", 100) < 70:
            recommendations.append("Warning: Signal degradation observed. Monitor communication link quality.")

        sensor = scores.get("sensor_status", {})
        if sensor.get("score", 100) < 80:
            recommendations.append("Warning: Sensor status degraded. Some sensors may have failed. Run diagnostics.")

        cpu = scores.get("cpu_usage_pct", {})
        if cpu.get("score", 100) < 50:
            recommendations.append("Warning: CPU usage is critically high. Check for runaway processes.")

        memory = scores.get("memory_usage_pct", {})
        if memory.get("score", 100) < 50:
            recommendations.append("Warning: Memory usage is critically high. Consider memory cleanup or reboot.")

        if not recommendations:
            recommendations.append("All systems nominal. No immediate action required.")

        return recommendations

    def compute_batch_health(self, df: pd.DataFrame) -> pd.DataFrame:
        records = []
        for sat_id in df["satellite_id"].unique():
            sat_df = df[df["satellite_id"] == sat_id]
            health = self.compute_health(sat_df)
            records.append({
                "satellite_id": sat_id,
                "timestamp": datetime.utcnow(),
                "health_score": health["overall_score"],
                "battery_score": health["metric_scores"].get("battery_pct", {}).get("score", 0),
                "temperature_score": health["metric_scores"].get("temperature_c", {}).get("score", 0),
                "signal_score": health["metric_scores"].get("signal_strength_dbm", {}).get("score", 0),
                "cpu_score": health["metric_scores"].get("cpu_usage_pct", {}).get("score", 0),
                "memory_score": health["metric_scores"].get("memory_usage_pct", {}).get("score", 0),
                "radiation_score": health["metric_scores"].get("radiation_level", {}).get("score", 0),
                "solar_power_score": health["metric_scores"].get("solar_voltage_v", {}).get("score", 0),
                "sensor_score": health["metric_scores"].get("sensor_status", {}).get("score", 0),
                "overall_status": health["status"],
            })
        return pd.DataFrame(records)
