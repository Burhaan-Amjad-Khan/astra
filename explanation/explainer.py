"""ASTRA AI Explanation Engine - Human-Readable Insights from Calculated Data"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.helpers import setup_logging, health_category

logger = setup_logging("astra.explanation")


class ExplanationEngine:
    """Generates human-readable explanations from calculated analytics results.
    NEVER invents values - only uses computed results passed as input."""

    def __init__(self):
        self._templates = {
            "engineer": self._explain_engineer,
            "scientist": self._explain_scientist,
            "student": self._explain_student,
        }

    def explain(self, data: Dict[str, Any], mode: str = "engineer") -> str:
        explainer = self._templates.get(mode, self._explain_engineer)
        return explainer(data)

    def _explain_engineer(self, data: Dict) -> str:
        parts = []
        score = data.get("health_score", data.get("overall_score", 0))
        hc = health_category(score)

        parts.append(f"=== ASTRA Telemetry Analysis Report ===")
        parts.append(f"Timestamp: {data.get('timestamp', datetime.utcnow().isoformat())}")
        parts.append(f"Satellite: {data.get('satellite_id', 'Unknown')}")
        parts.append(f"Overall Health Score: {score:.1f}/100 ({hc['category']})")
        parts.append("")

        metrics = data.get("metrics", data.get("metric_scores", {}))
        if metrics:
            parts.append("--- Metric Analysis ---")
            for name, info in metrics.items():
                if isinstance(info, dict):
                    val = info.get("value", "N/A")
                    met_score = info.get("score", "N/A")
                    status = info.get("status", "N/A")
                    unit = info.get("unit", "")
                    parts.append(f"  {name}: {val} {unit} | Score: {met_score} | Status: {status}")

        stats = data.get("statistics", data.get("stats", {}))
        if stats:
            parts.append("")
            parts.append("--- Statistical Summary ---")
            for name, info in list(stats.items())[:5]:
                if isinstance(info, dict):
                    parts.append(f"  {name}: mean={info.get('mean', 'N/A')}, std={info.get('std', 'N/A')}")

        trends = data.get("trends", {})
        if trends:
            parts.append("")
            parts.append("--- Trend Analysis ---")
            for name, info in trends.items():
                if isinstance(info, dict):
                    parts.append(f"  {name}: {info.get('direction', 'stable')} (slope: {info.get('slope', 0):.4f})")

        anomalies = data.get("anomalies", data.get("anomaly_summary", {}))
        if isinstance(anomalies, dict) and anomalies.get("total_anomalies", 0) > 0:
            parts.append("")
            parts.append("--- Anomaly Report ---")
            parts.append(f"  Total Anomalies: {anomalies['total_anomalies']}")
            parts.append(f"  Severity: {anomalies.get('severity', 'N/A')}")
            parts.append(f"  {anomalies.get('summary', '')}")

        relationships = data.get("correlations", data.get("relationships", []))
        if relationships:
            parts.append("")
            parts.append("--- Key Correlations ---")
            for rel in relationships[:5]:
                parts.append(f"  {rel['name']}: r={rel['correlation']:.3f} ({rel['strength']} {rel['direction']})")

        recommendations = data.get("recommendations", [])
        if recommendations:
            parts.append("")
            parts.append("--- Recommendations ---")
            for rec in recommendations:
                parts.append(f"  - {rec}")

        return "\n".join(parts)

    def _explain_scientist(self, data: Dict) -> str:
        parts = []
        score = data.get("health_score", data.get("overall_score", 0))
        hc = health_category(score)

        parts.append(f"ASTRA Scientific Telemetry Report")
        parts.append(f"Satellite: {data.get('satellite_id', 'Unknown')}")
        parts.append(f"Health Score: {score:.1f}/100 — {hc['category']}")
        parts.append("")

        metrics = data.get("metrics", data.get("metric_scores", {}))
        if metrics:
            battery = metrics.get("battery_pct", {})
            temp = metrics.get("temperature_c", {})
            signal = metrics.get("signal_strength_dbm", {})

            parts.append("Key Telemetry Values:")
            if battery:
                parts.append(f"  Battery: {battery.get('value', 'N/A')}% — {battery.get('status', 'N/A')}")
            if temp:
                parts.append(f"  Temperature: {temp.get('value', 'N/A')}°C — {temp.get('status', 'N/A')}")
            if signal:
                parts.append(f"  Signal: {signal.get('value', 'N/A')} dBm — {signal.get('status', 'N/A')}")

        stats = data.get("statistics", data.get("stats", {}))
        if stats:
            parts.append("")
            parts.append("Distribution Characteristics:")
            dist_info = data.get("distributions", {})
            for name, info in stats.items():
                if isinstance(info, dict) and name in dist_info:
                    dist = dist_info[name]
                    parts.append(f"  {name}: {dist.get('distribution_type', 'N/A')} "
                               f"(skew={dist.get('skewness', 0):.2f}, kurt={dist.get('kurtosis', 0):.2f})")

        return "\n".join(parts)

    def _explain_student(self, data: Dict) -> str:
        score = data.get("health_score", data.get("overall_score", 0))
        hc = health_category(score)
        sat_id = data.get("satellite_id", "Unknown")

        lines = [f"Satellite {sat_id} Report"]
        lines.append("")

        if score >= 90:
            lines.append(f"Health: {score:.0f}/100 - Excellent!")
            lines.append(f"The satellite is working perfectly. All systems are healthy and performing well.")
        elif score >= 70:
            lines.append(f"Health: {score:.0f}/100 - Good")
            lines.append(f"The satellite is working well. Most systems are healthy with some minor issues to watch.")
        elif score >= 40:
            lines.append(f"Health: {score:.0f}/100 - Needs Attention")
            lines.append(f"The satellite needs attention. Some systems are not working as expected and should be checked.")
        else:
            lines.append(f"Health: {score:.0f}/100 - Critical!")
            lines.append(f"The satellite needs immediate attention. Important systems are not working properly.")

        metrics = data.get("metrics", data.get("metric_scores", {}))
        if metrics:
            battery = metrics.get("battery_pct", {})
            temp = metrics.get("temperature_c", {})
            signal = metrics.get("signal_strength_dbm", {})

            lines.append("")
            lines.append("System Status:")
            if battery:
                b_val = battery.get("status", "N/A")
                b_emoji = "Green" if battery.get("score", 0) >= 70 else "Orange" if battery.get("score", 0) >= 40 else "Red"
                lines.append(f"  Battery: {b_val} ({b_emoji})")
            if temp:
                t_val = temp.get("status", "N/A")
                t_emoji = "Green" if temp.get("score", 0) >= 70 else "Orange" if temp.get("score", 0) >= 40 else "Red"
                lines.append(f"  Temperature: {t_val} ({t_emoji})")
            if signal:
                s_val = signal.get("status", "N/A")
                s_emoji = "Green" if signal.get("score", 0) >= 70 else "Orange" if signal.get("score", 0) >= 40 else "Red"
                lines.append(f"  Signal: {s_val} ({s_emoji})")

        recommendations = data.get("recommendations", [])
        if recommendations:
            lines.append("")
            lines.append("What to do:")
            for rec in recommendations[:3]:
                lines.append(f"  - {rec}")

        return "\n".join(lines)

    def explain_anomaly(self, anomaly_data: List[Dict[str, Any]], mode: str = "engineer") -> str:
        if not anomaly_data:
            return "No anomalies detected during the observation period."

        parts = [f"Anomaly Detection Report — {len(anomaly_data)} events found"]
        parts.append("")

        type_descriptions = {
            "temperature_spike": "Sudden temperature increase detected. The thermal control system may be under stress or external heating may be occurring.",
            "battery_drop": "Rapid battery level decrease observed. This may indicate a power system issue or increased power consumption.",
            "signal_loss": "Signal degradation detected. Communication quality has dropped, possibly due to antenna misalignment or atmospheric interference.",
            "cpu_overload": "CPU usage spike detected. The onboard processor may be under heavy computational load.",
            "memory_overload": "Memory usage spike detected. Available memory may be insufficient for current operations.",
        }

        for anomaly in anomaly_data[:10]:
            atype = anomaly.get("type", "unknown")
            desc = type_descriptions.get(atype, f"Anomaly of type '{atype}' detected.")
            parts.append(f"[{anomaly.get('severity', 'Medium')}] {desc}")
            parts.append(f"  Metric: {anomaly.get('metric', 'N/A')} = {anomaly.get('value', 'N/A')} {anomaly.get('unit', '')}")
            parts.append(f"  Time: {anomaly.get('timestamp', 'N/A')}")
            parts.append("")

        if len(anomaly_data) > 10:
            parts.append(f"... and {len(anomaly_data) - 10} more events.")

        return "\n".join(parts)

    def explain_health(self, health_data: Dict[str, Any], mode: str = "engineer") -> str:
        return self.explain(health_data, mode)

    def generate_insight_card(self, title: str, metrics: Dict[str, Any],
                              insights: List[str]) -> Dict[str, Any]:
        return {
            "title": title,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "insights": insights,
            "summary": " | ".join(insights) if insights else "All systems nominal.",
        }
