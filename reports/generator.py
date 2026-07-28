"""ASTRA Report Generator - PDF, Excel, CSV Export"""

import pandas as pd
import numpy as np
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import csv

from config.settings import REPORTS_DIR, EXPORTS_DIR
from utils.helpers import setup_logging

logger = setup_logging("astra.reports")


class ReportGenerator:
    def __init__(self):
        self.reports_dir = REPORTS_DIR
        self.exports_dir = EXPORTS_DIR

    def export_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        if filename is None:
            filename = f"telemetry_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.exports_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"CSV exported: {filepath}")
        return str(filepath)

    def export_excel(self, df_dict: Dict[str, pd.DataFrame], filename: str = None) -> str:
        if filename is None:
            filename = f"telemetry_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = self.exports_dir / filename

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            for sheet_name, df in df_dict.items():
                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)

        logger.info(f"Excel report exported: {filepath}")
        return str(filepath)

    def generate_telemetry_report_data(self, satellite_id: str, df: pd.DataFrame,
                                       stats: Dict, health: Dict,
                                       anomalies: Dict, explanation: str) -> Dict[str, Any]:
        return {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "satellite_id": satellite_id,
                "report_type": "Telemetry Analysis Report",
                "total_records": len(df),
                "data_source": "simulated",
            },
            "health_assessment": {
                "score": health.get("overall_score", 0),
                "status": health.get("status", "Unknown"),
                "recommendations": health.get("recommendations", []),
            },
            "statistical_summary": stats.get("summary", {}),
            "anomaly_report": anomalies,
            "ai_insights": explanation,
        }

    def export_json_report(self, report_data: Dict[str, Any], filename: str = None) -> str:
        if filename is None:
            sat_id = report_data.get("report_metadata", {}).get("satellite_id", "unknown")
            filename = f"report_{sat_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.reports_dir / filename

        with open(filepath, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"JSON report exported: {filepath}")
        return str(filepath)

    def generate_summary_csv(self, health_scores: pd.DataFrame,
                             anomaly_counts: Dict[str, int]) -> str:
        filename = f"fleet_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.exports_dir / filename

        summary = health_scores.copy()
        summary["anomaly_count"] = summary["satellite_id"].map(
            lambda x: anomaly_counts.get(x, 0)
        )

        summary.to_csv(filepath, index=False)
        logger.info(f"Fleet summary CSV exported: {filepath}")
        return str(filepath)

    def get_csv_bytes(self, df: pd.DataFrame) -> bytes:
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    def get_excel_bytes(self, df_dict: Dict[str, pd.DataFrame]) -> bytes:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        buffer.seek(0)
        return buffer.getvalue()

    def get_json_bytes(self, report_data: Dict[str, Any]) -> bytes:
        return json.dumps(report_data, indent=2, default=str).encode("utf-8")
