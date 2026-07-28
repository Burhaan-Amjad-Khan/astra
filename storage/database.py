"""ASTRA Database Layer - DuckDB with PostgreSQL-ready design"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from config.settings import DATABASE_PATH
from utils.helpers import setup_logging

logger = setup_logging("astra.storage")


class TelemetryDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._initialized = False

    def connect(self):
        self.conn = duckdb.connect(str(self.db_path))
        self.conn.execute("INSTALL httpfs; LOAD httpfs;")
        logger.info(f"Connected to database: {self.db_path}")

    def initialize(self):
        if not self.conn:
            self.connect()

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS satellites (
                satellite_id VARCHAR PRIMARY KEY,
                name VARCHAR,
                mission_type VARCHAR,
                launch_date TIMESTAMP,
                orbit_type VARCHAR,
                status VARCHAR DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id BIGINT PRIMARY KEY,
                satellite_id VARCHAR,
                timestamp TIMESTAMP,
                latitude DOUBLE,
                longitude DOUBLE,
                altitude_km DOUBLE,
                velocity_kms DOUBLE,
                orbit_number INTEGER,
                battery_pct DOUBLE,
                solar_voltage_v DOUBLE,
                current_a DOUBLE,
                temperature_c DOUBLE,
                cpu_usage_pct DOUBLE,
                memory_usage_pct DOUBLE,
                signal_strength_dbm DOUBLE,
                radiation_level DOUBLE,
                gyro_x DOUBLE,
                gyro_y DOUBLE,
                gyro_z DOUBLE,
                accel_x DOUBLE,
                accel_y DOUBLE,
                accel_z DOUBLE,
                sensor_status INTEGER,
                comm_status INTEGER,
                mission_status VARCHAR,
                data_source VARCHAR DEFAULT 'simulated',
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id BIGINT PRIMARY KEY,
                satellite_id VARCHAR,
                timestamp TIMESTAMP,
                health_score DOUBLE,
                battery_score DOUBLE,
                temperature_score DOUBLE,
                signal_score DOUBLE,
                cpu_score DOUBLE,
                memory_score DOUBLE,
                radiation_score DOUBLE,
                solar_power_score DOUBLE,
                sensor_score DOUBLE,
                overall_status VARCHAR,
                FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_records (
                id BIGINT PRIMARY KEY,
                satellite_id VARCHAR,
                timestamp TIMESTAMP,
                anomaly_type VARCHAR,
                severity VARCHAR,
                description VARCHAR,
                affected_metric VARCHAR,
                metric_value DOUBLE,
                expected_range VARCHAR,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_reports (
                id BIGINT PRIMARY KEY,
                satellite_id VARCHAR,
                timestamp TIMESTAMP,
                quality_score DOUBLE,
                missing_count INTEGER,
                duplicate_count INTEGER,
                invalid_count INTEGER,
                issues TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id)
            )
        """)

        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_telemetry_id START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_health_id START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_anomaly_id START 1;
            CREATE SEQUENCE IF NOT EXISTS seq_validation_id START 1;
        """)

        self._initialized = True
        logger.info("Database schema initialized")

    def insert_telemetry_batch(self, df: pd.DataFrame):
        if not self._initialized:
            self.initialize()
        df = df.copy()
        if "id" not in df.columns:
            self.conn.execute(
                f"SELECT nextval('seq_telemetry_id') FROM generate_series(1, {len(df)})"
            )
            ids = self.conn.fetchall()
            df["id"] = [r[0] for r in ids]
        self.conn.register("_batch", df)
        self.conn.execute("INSERT INTO telemetry SELECT * FROM _batch")
        self.conn.unregister("_batch")
        logger.info(f"Inserted {len(df)} telemetry records")

    def query(self, sql: str) -> pd.DataFrame:
        if not self._initialized:
            self.initialize()
        return self.conn.execute(sql).df()

    def get_satellite_telemetry(
        self, satellite_id: str, limit: Optional[int] = None
    ) -> pd.DataFrame:
        clause = f"WHERE satellite_id = '{satellite_id}' ORDER BY timestamp DESC"
        if limit:
            clause += f" LIMIT {limit}"
        return self.query(f"SELECT * FROM telemetry {clause}")

    def get_all_satellites(self) -> pd.DataFrame:
        return self.query("SELECT * FROM satellites WHERE status = 'active'")

    def get_summary_stats(self) -> Dict[str, Any]:
        return {
            "total_satellites": self.query(
                "SELECT COUNT(DISTINCT satellite_id) FROM telemetry"
            ).iloc[0, 0],
            "total_records": self.query(
                "SELECT COUNT(*) FROM telemetry"
            ).iloc[0, 0],
            "db_size": self._get_db_size(),
        }

    def _get_db_size(self) -> str:
        from utils.helpers import format_bytes
        return format_bytes(self.db_path.stat().st_size if self.db_path.exists() else 0)

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
