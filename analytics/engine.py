"""ASTRA Analytics Engine - Statistics, Time Series, Correlation"""

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from utils.helpers import setup_logging

logger = setup_logging("astra.analytics")

NUMERIC_TELEMETRY_COLS = [
    "altitude_km", "velocity_kms", "battery_pct", "solar_voltage_v",
    "current_a", "temperature_c", "cpu_usage_pct", "memory_usage_pct",
    "signal_strength_dbm", "radiation_level", "gyro_x", "gyro_y",
    "gyro_z", "accel_x", "accel_y", "accel_z",
]


@dataclass
class ColumnStats:
    mean: float
    median: float
    mode: float
    min: float
    max: float
    range_value: float
    variance: float
    std_dev: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    skewness: float
    kurtosis: float
    count: int
    missing: int
    iqr: float


class AnalyticsEngine:
    def __init__(self):
        pass

    def compute_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info(f"Computing statistics for {len(df)} records")
        result = {"record_count": len(df), "columns": {}}

        for col in NUMERIC_TELEMETRY_COLS:
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if len(series) == 0:
                continue

            result["columns"][col] = ColumnStats(
                mean=float(series.mean()),
                median=float(series.median()),
                mode=float(series.mode().iloc[0]) if len(series.mode()) > 0 else 0.0,
                min=float(series.min()),
                max=float(series.max()),
                range_value=float(series.max() - series.min()),
                variance=float(series.var()),
                std_dev=float(series.std()),
                p25=float(np.percentile(series, 25)),
                p50=float(np.percentile(series, 50)),
                p75=float(np.percentile(series, 75)),
                p90=float(np.percentile(series, 90)),
                p95=float(np.percentile(series, 95)),
                p99=float(np.percentile(series, 99)),
                skewness=float(scipy_stats.skew(series)),
                kurtosis=float(scipy_stats.kurtosis(series)),
                count=int(len(series)),
                missing=int(df[col].isnull().sum()),
                iqr=float(np.percentile(series, 75) - np.percentile(series, 25)),
            )

        result["summary"] = self._summarize_stats(result["columns"])
        return result

    def _summarize_stats(self, col_stats: Dict[str, ColumnStats]) -> Dict:
        summary = {}
        for name, stats in col_stats.items():
            summary[name] = {
                "mean": stats.mean,
                "std": stats.std_dev,
                "min": stats.min,
                "max": stats.max,
                "unit": self._get_unit(name),
            }
        return summary

    def _get_unit(self, col: str) -> str:
        units = {
            "altitude_km": "km", "velocity_kms": "km/s",
            "battery_pct": "%", "solar_voltage_v": "V",
            "current_a": "A", "temperature_c": "C",
            "cpu_usage_pct": "%", "memory_usage_pct": "%",
            "signal_strength_dbm": "dBm", "radiation_level": "rad",
            "gyro_x": "deg/s", "gyro_y": "deg/s", "gyro_z": "deg/s",
            "accel_x": "g", "accel_y": "g", "accel_z": "g",
        }
        return units.get(col, "")

    def compute_correlation(self, df: pd.DataFrame) -> pd.DataFrame:
        nums = df.select_dtypes(include=[np.number])
        corr_columns = [c for c in NUMERIC_TELEMETRY_COLS if c in nums.columns]
        if len(corr_columns) < 2:
            return pd.DataFrame()
        corr_matrix = nums[corr_columns].corr()
        logger.info(f"Computed correlation matrix for {len(corr_columns)} columns")
        return corr_matrix

    def analyze_relationships(self, df: pd.DataFrame) -> List[Dict]:
        relationships = []
        pairs = [
            ("battery_pct", "temperature_c", "Battery vs Temperature"),
            ("battery_pct", "signal_strength_dbm", "Battery vs Signal"),
            ("altitude_km", "temperature_c", "Altitude vs Temperature"),
            ("solar_voltage_v", "battery_pct", "Solar Power vs Battery"),
            ("cpu_usage_pct", "temperature_c", "CPU vs Temperature"),
            ("signal_strength_dbm", "altitude_km", "Signal vs Altitude"),
            ("radiation_level", "altitude_km", "Radiation vs Altitude"),
        ]

        for col1, col2, name in pairs:
            if col1 in df.columns and col2 in df.columns:
                s1, s2 = df[col1].dropna(), df[col2].dropna()
                common_idx = s1.index.intersection(s2.index)
                if len(common_idx) > 2:
                    corr = scipy_stats.pearsonr(s1[common_idx], s2[common_idx])
                    relationships.append({
                        "name": name,
                        "correlation": round(corr.statistic, 4),
                        "p_value": round(corr.pvalue, 6),
                        "strength": self._correlation_strength(abs(corr.statistic)),
                        "direction": "positive" if corr.statistic > 0 else "negative",
                    })

        return sorted(relationships, key=lambda x: abs(x["correlation"]), reverse=True)

    def _correlation_strength(self, abs_val: float) -> str:
        if abs_val >= 0.8:
            return "very strong"
        elif abs_val >= 0.6:
            return "strong"
        elif abs_val >= 0.4:
            return "moderate"
        elif abs_val >= 0.2:
            return "weak"
        return "very weak"

    def time_series_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info(f"Running time series analysis on {len(df)} records")
        result = {"trends": {}, "moving_averages": {}, "rates_of_change": {}}

        time_cols = [
            "battery_pct", "temperature_c", "signal_strength_dbm",
            "altitude_km", "cpu_usage_pct", "solar_voltage_v", "radiation_level",
        ]

        for col in time_cols:
            if col not in df.columns:
                continue
            series = df.set_index("timestamp")[col].dropna()
            if len(series) < 10:
                continue

            try:
                window = max(5, len(series) // 20)
                result["moving_averages"][col] = series.rolling(window=window, center=True).mean()

                if len(series) >= 3:
                    x = np.arange(len(series))
                    slope, intercept = np.polyfit(x, series.values, 1)
                    result["trends"][col] = {
                        "slope": float(slope),
                        "direction": "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable",
                        "magnitude": abs(slope),
                        "unit_per_sample": round(slope, 6),
                    }

                roc = series.diff() / series.shift(1).abs() * 100
                result["rates_of_change"][col] = {
                    "mean_roc_pct": round(float(roc.mean()), 4),
                    "max_increase_pct": round(float(roc.max()), 4),
                    "max_decrease_pct": round(float(roc.min()), 4),
                    "volatility": round(float(roc.std()), 4),
                }
            except Exception as e:
                logger.warning(f"Time series analysis failed for {col}: {e}")

        return result

    def distribution_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        result = {}
        for col in ["battery_pct", "temperature_c", "signal_strength_dbm", "altitude_km"]:
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if len(series) < 10:
                continue

            stat, p_value = scipy_stats.normaltest(series)
            result[col] = {
                "is_normal": bool(p_value > 0.05),
                "normality_p_value": float(p_value),
                "skewness": float(scipy_stats.skew(series)),
                "kurtosis": float(scipy_stats.kurtosis(series)),
                "distribution_type": self._classify_distribution(float(scipy_stats.skew(series))),
            }

        return result

    def _classify_distribution(self, skewness: float) -> str:
        if abs(skewness) < 0.5:
            return "symmetric"
        elif skewness > 0:
            return "right-skewed" if skewness > 1 else "slightly right-skewed"
        else:
            return "left-skewed" if skewness < -1 else "slightly left-skewed"
