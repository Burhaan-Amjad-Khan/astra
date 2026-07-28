"""ASTRA Data Validation Engine"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime

from config.settings import VALIDATION_CONFIG
from utils.helpers import setup_logging

logger = setup_logging("astra.validation")


class ValidationEngine:
    def __init__(self):
        self.config = VALIDATION_CONFIG
        self._expected_columns = [
            "satellite_id", "timestamp", "latitude", "longitude",
            "altitude_km", "velocity_kms", "orbit_number", "battery_pct",
            "solar_voltage_v", "current_a", "temperature_c", "cpu_usage_pct",
            "memory_usage_pct", "signal_strength_dbm", "radiation_level",
            "gyro_x", "gyro_y", "gyro_z", "accel_x", "accel_y", "accel_z",
            "sensor_status", "comm_status", "mission_status",
        ]

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info(f"Validating dataframe with {len(df)} rows and {len(df.columns)} columns")
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_records": len(df),
            "total_columns": len(df.columns),
            "missing_columns": [],
            "quality_score": 100.0,
            "issues": [],
            "details": {},
        }

        report.update(self._check_missing_columns(df))
        report.update(self._check_missing_values(df))
        report.update(self._check_duplicates(df))
        report.update(self._check_data_types(df))
        report.update(self._check_value_ranges(df))
        report.update(self._check_timestamps(df))
        report.update(self._calculate_quality_score(report))

        logger.info(f"Validation complete. Quality score: {report['quality_score']:.1f}%")
        return report

    def _check_missing_columns(self, df: pd.DataFrame) -> Dict:
        missing = [c for c in self._expected_columns if c not in df.columns]
        return {
            "missing_columns": missing,
            "column_check_passed": len(missing) == 0,
        }

    def _check_missing_values(self, df: pd.DataFrame) -> Dict:
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        total_missing = missing.sum()
        missing_details = {}
        issues = []

        for col in missing.index:
            if missing[col] > 0:
                missing_details[col] = {
                    "count": int(missing[col]),
                    "percentage": float(missing_pct[col]),
                }
                if missing_pct[col] > self.config["max_missing_pct"]:
                    issues.append(
                        f"Column '{col}' has {missing_pct[col]:.1f}% missing values "
                        f"(threshold: {self.config['max_missing_pct']}%)"
                    )

        return {
            "missing_values": missing_details,
            "missing_total": int(total_missing),
            "missing_pct_total": float(round(total_missing / max(1, len(df) * len(df.columns)) * 100, 2)),
        }

    def _check_duplicates(self, df: pd.DataFrame) -> Dict:
        dup_count = df.duplicated().sum()
        dup_pct = round(dup_count / max(1, len(df)) * 100, 2)
        return {
            "duplicate_count": int(dup_count),
            "duplicate_pct": float(dup_pct),
            "duplicate_issue": dup_pct > self.config["max_duplicate_pct"],
        }

    def _check_data_types(self, df: pd.DataFrame) -> Dict:
        issues = []
        numeric_cols = [
            "latitude", "longitude", "altitude_km", "velocity_kms",
            "battery_pct", "solar_voltage_v", "current_a", "temperature_c",
            "cpu_usage_pct", "memory_usage_pct", "signal_strength_dbm",
            "radiation_level", "gyro_x", "gyro_y", "gyro_z",
            "accel_x", "accel_y", "accel_z",
        ]
        for col in numeric_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"Column '{col}' is not numeric")
        return {"dtype_issues": issues, "dtype_ok": len(issues) == 0}

    def _check_value_ranges(self, df: pd.DataFrame) -> Dict:
        ranges = {
            "battery_pct": self.config["battery_range"],
            "temperature_c": self.config["temperature_range"],
            "altitude_km": self.config["altitude_range"],
            "velocity_kms": self.config["velocity_range"],
            "solar_voltage_v": self.config["solar_voltage_range"],
            "current_a": self.config["current_range"],
            "cpu_usage_pct": self.config["cpu_range"],
            "memory_usage_pct": self.config["memory_range"],
            "signal_strength_dbm": self.config["signal_range"],
            "radiation_level": self.config["radiation_range"],
            "gyro_x": self.config["gyro_range"],
            "gyro_y": self.config["gyro_range"],
            "gyro_z": self.config["gyro_range"],
            "accel_x": self.config["accel_range"],
            "accel_y": self.config["accel_range"],
            "accel_z": self.config["accel_range"],
        }
        range_violations = {}
        for col, (low, high) in ranges.items():
            if col not in df.columns:
                continue
            out_of_range = df[(df[col] < low) | (df[col] > high)]
            if len(out_of_range) > 0:
                range_violations[col] = {
                    "count": len(out_of_range),
                    "expected": f"[{low}, {high}]",
                    "actual_range": f"[{df[col].min():.2f}, {df[col].max():.2f}]",
                }
        return {
            "range_violations": range_violations,
            "range_ok": len(range_violations) == 0,
        }

    def _check_timestamps(self, df: pd.DataFrame) -> Dict:
        issues = []
        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                try:
                    pd.to_datetime(df["timestamp"])
                except Exception:
                    issues.append("Timestamp column cannot be parsed as datetime")

            if pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                duplicates = df["timestamp"].duplicated().sum()
                if duplicates > 0:
                    issues.append(f"{duplicates} duplicate timestamps found")

                gaps = df["timestamp"].diff().dropna()
                if len(gaps) > 0:
                    median_gap = gaps.median()
                    large_gaps = gaps[gaps > median_gap * 5]
                    if len(large_gaps) > 0:
                        issues.append(f"{len(large_gaps)} unusually large timestamp gaps detected")

        return {"timestamp_issues": issues, "timestamp_ok": len(issues) == 0}

    def _calculate_quality_score(self, report: Dict) -> Dict:
        deductions = 0

        if report.get("missing_pct_total", 0) > 0:
            deductions += min(30, report["missing_pct_total"])

        if report.get("duplicate_pct", 0) > 0:
            deductions += min(20, report["duplicate_pct"] * 2)

        if not report.get("column_check_passed", True):
            deductions += len(report.get("missing_columns", [])) * 5

        if not report.get("dtype_ok", True):
            deductions += len(report.get("dtype_issues", [])) * 3

        if not report.get("range_ok", True):
            for v in report.get("range_violations", {}).values():
                deductions += min(10, v["count"] * 0.1)

        if not report.get("timestamp_ok", True):
            deductions += len(report.get("timestamp_issues", [])) * 5

        quality = max(0, 100 - deductions)
        report["quality_score"] = round(quality, 1)
        report["deductions"] = round(deductions, 1)

        all_issues = []
        if not report.get("column_check_passed"):
            all_issues.append(f"Missing columns: {report['missing_columns']}")
        for issue in report.get("dtype_issues", []):
            all_issues.append(issue)
        for col, v in report.get("range_violations", {}).items():
            all_issues.append(f"Range violation in {col}: {v['count']} values outside {v['expected']}")
        for issue in report.get("timestamp_issues", []):
            all_issues.append(issue)

        report["all_issues"] = all_issues
        return report

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"Cleaning dataframe with {len(df)} rows")
        df = df.copy()

        df = df.drop_duplicates()

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = df[col].ffill().bfill()

        rows_before = len(df)
        df = df.dropna(thresh=len(df.columns) * 0.5)
        logger.info(f"Cleaned: {rows_before} -> {len(df)} rows (removed {rows_before - len(df)})")
        return df
