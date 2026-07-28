"""ASTRA Telemetry Simulator - Realistic Satellite Data Generator"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from config.settings import SIMULATION_CONFIG
from utils.helpers import setup_logging

logger = setup_logging("astra.simulator")

ORBIT_TYPES = ["LEO", "MEO", "GEO", "SSO", "HEO"]
MISSION_TYPES = ["Earth Observation", "Communications", "Navigation",
                 "Scientific", "Weather", "Reconnaissance", "Technology Demo"]
SATELLITE_NAMES = [
    "Aryabhata", "Bhaskara", "Rohini", "INSAT", "IRS", "Cartosat",
    "Oceansat", "Resourcesat", "RISAT", "GSAT", "IRNSS", "NavIC",
    "EMISAT", "HySIS", "Microsat", "Astrosat", "Chandrayaan", "Mangalyaan",
]


@dataclass
class SatelliteProfile:
    satellite_id: str
    name: str
    mission_type: str
    orbit_type: str
    altitude_nominal: float
    inclination: float
    period_minutes: float
    eccentricity: float
    raan: float
    arg_perigee: float
    mean_anomaly: float
    battery_capacity: float = 100.0
    solar_efficiency: float = 1.0
    thermal_limit: float = 80.0


class TelemetrySimulator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or SIMULATION_CONFIG["seed"]
        np.random.seed(self.seed)
        self.sampling_interval = SIMULATION_CONFIG["sampling_interval_seconds"]
        self.satellites: Dict[str, SatelliteProfile] = {}
        self._anomaly_configs: Dict[str, Dict] = {}

    def generate_satellites(self, count: int = 10) -> List[SatelliteProfile]:
        logger.info(f"Generating {count} satellite profiles")
        self.satellites.clear()

        for i in range(count):
            sat_num = i + 1
            sat_id = f"SAT-{sat_num:04d}"
            name_idx = i % len(SATELLITE_NAMES)
            orbit_type = np.random.choice(ORBIT_TYPES)

            if orbit_type == "LEO":
                altitude = np.random.uniform(300, 1200)
                period = 90 + (altitude - 300) * 0.02
            elif orbit_type == "MEO":
                altitude = np.random.uniform(5000, 20000)
                period = 120 + altitude * 0.005
            elif orbit_type == "GEO":
                altitude = 35786
                period = 1440
            elif orbit_type == "SSO":
                altitude = np.random.uniform(600, 800)
                period = 96 + (altitude - 600) * 0.01
            else:
                altitude = np.random.uniform(1000, 20000)
                period = 100 + altitude * 0.01

            profile = SatelliteProfile(
                satellite_id=sat_id,
                name=f"{SATELLITE_NAMES[name_idx]}-{sat_num}",
                mission_type=np.random.choice(MISSION_TYPES),
                orbit_type=orbit_type,
                altitude_nominal=altitude,
                inclination=np.random.uniform(0, 98) if orbit_type != "SSO" else 97.5,
                period_minutes=period,
                eccentricity=np.random.uniform(0, 0.05),
                raan=np.random.uniform(0, 360),
                arg_perigee=np.random.uniform(0, 360),
                mean_anomaly=np.random.uniform(0, 360),
                battery_capacity=100.0,
                solar_efficiency=np.random.uniform(0.85, 1.0),
                thermal_limit=80.0,
            )
            self.satellites[sat_id] = profile

        logger.info(f"Generated {len(self.satellites)} satellite profiles")
        return list(self.satellites.values())

    def add_anomaly_scenario(self, satellite_id: str, anomaly_type: str,
                             start_index: int, duration: int, severity: float = 1.0):
        if satellite_id not in self._anomaly_configs:
            self._anomaly_configs[satellite_id] = {}
        key = f"{anomaly_type}_{start_index}"
        self._anomaly_configs[satellite_id][key] = {
            "type": anomaly_type,
            "start": start_index,
            "duration": duration,
            "severity": severity,
        }

    def generate_telemetry(
        self,
        count: int = None,
        readings: int = None,
        start_time: Optional[datetime] = None,
        include_anomalies: bool = True,
    ) -> pd.DataFrame:
        if count is None:
            count = SIMULATION_CONFIG["default_satellite_count"]
        if readings is None:
            readings = SIMULATION_CONFIG["default_readings_per_satellite"]

        if not self.satellites:
            self.generate_satellites(count)

        if start_time is None:
            start_time = datetime.utcnow() - timedelta(
                minutes=readings * self.sampling_interval / 60
            )

        records = []

        for sat_id, profile in self.satellites.items():
            sat_records = self._generate_satellite_data(
                profile, readings, start_time, include_anomalies
            )
            records.extend(sat_records)

        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} telemetry records for {len(self.satellites)} satellites")
        return df

    def _generate_satellite_data(
        self, profile: SatelliteProfile, readings: int,
        start_time: datetime, include_anomalies: bool
    ) -> List[Dict]:
        records = []
        time_step = timedelta(seconds=self.sampling_interval)
        orbit_period_readings = int(profile.period_minutes * 60 / self.sampling_interval)

        base_lat = np.random.uniform(-60, 60)
        base_lon = np.random.uniform(0, 360)
        lat_drift = np.random.uniform(-3, 3) / readings
        lon_drift = np.random.uniform(-3, 3) / readings

        battery = 100.0
        solar_voltage = 32.0
        temperature = 25.0
        signal_base = -45.0
        radiation_base = np.random.uniform(10, 50)
        cpu_base = np.random.uniform(20, 40)
        memory_base = np.random.uniform(30, 50)

        body_rate = 2 * np.pi / orbit_period_readings

        anomalies = self._anomaly_configs.get(profile.satellite_id, {}) if include_anomalies else {}

        for i in range(readings):
            ts = start_time + i * time_step
            anomaly_effects = self._get_anomaly_effects(anomalies, i, readings)

            phase = i * body_rate
            eclipse_factor = 0.5 * (1 + np.sin(phase))
            altitude_variation = profile.eccentricity * profile.altitude_nominal * np.sin(phase)
            altitude = profile.altitude_nominal + altitude_variation + np.random.normal(0, 0.5)
            velocity = 7.8 - (altitude - 300) * 0.0005 + np.random.normal(0, 0.02)

            lat = (base_lat + lat_drift * i + 30 * np.sin(phase * 0.3)) % 180 - 90
            lon = (base_lon + lon_drift * i + 60 * phase / (2 * np.pi)) % 360
            if lon > 180:
                lon -= 360

            orbit_num = i // orbit_period_readings + 1

            if anomaly_effects.get("battery_degradation", 0) > 0:
                battery -= anomaly_effects["battery_degradation"] * 2
            else:
                charge_rate = eclipse_factor * profile.solar_efficiency * 0.05
                discharge_rate = (1 - eclipse_factor) * 0.02
                battery += charge_rate - discharge_rate
                battery += np.random.normal(0, 0.3)
            battery = max(0, min(100, battery))

            solar_voltage = 32 * eclipse_factor * profile.solar_efficiency + np.random.normal(0, 0.5)
            solar_voltage = max(0, solar_voltage)

            current = solar_voltage / np.random.uniform(8, 12) + np.random.normal(0, 0.2)
            current = max(0, current)

            if anomaly_effects.get("temperature_spike", 0) > 0:
                temp_noise = np.random.normal(0, 3) + anomaly_effects["temperature_spike"] * 20
            else:
                temp_noise = np.random.normal(0, 1.5)
            temperature = 25 + 15 * (1 - eclipse_factor) + temp_noise
            temperature = max(-80, min(profile.thermal_limit + 40, temperature))

            cpu = cpu_base + 10 * np.sin(phase * 3) + np.random.normal(0, 2)
            if anomaly_effects.get("cpu_spike", 0) > 0:
                cpu += anomaly_effects["cpu_spike"] * 40
            cpu = max(0, min(100, cpu))

            memory = memory_base + 5 * np.sin(phase * 2) + np.random.normal(0, 1.5)
            if anomaly_effects.get("memory_spike", 0) > 0:
                memory += anomaly_effects["memory_spike"] * 40
            memory = max(0, min(100, memory))

            signal = signal_base + 10 * np.sin(phase * 0.5) + np.random.normal(0, 2)
            if anomaly_effects.get("signal_loss", 0) > 0:
                signal -= anomaly_effects["signal_loss"] * 30
            signal = max(-120, min(0, signal))

            radiation = radiation_base + 20 * np.sin(phase * 0.1) + np.random.normal(0, 3)
            radiation = max(0, radiation)

            gyro_x = 0.1 * np.sin(phase) + np.random.normal(0, 0.01)
            gyro_y = 0.1 * np.cos(phase) + np.random.normal(0, 0.01)
            gyro_z = 0.05 * np.sin(phase * 2) + np.random.normal(0, 0.01)

            accel_x = 0.01 * np.sin(phase * 3) + np.random.normal(0, 0.001)
            accel_y = 0.01 * np.cos(phase * 3) + np.random.normal(0, 0.001)
            accel_z = 0.005 * np.sin(phase * 5) + np.random.normal(0, 0.001)

            sensor_status = 1
            if anomaly_effects.get("sensor_failure", 0) > 0.5:
                sensor_status = 0

            comm_status = 1 if signal > -100 else 0

            mission_status = "Nominal"
            if anomaly_effects.get("battery_degradation", 0) > 0.3:
                mission_status = "Degraded"
            if anomaly_effects.get("sensor_failure", 0) > 0.5:
                mission_status = "Degraded"
            if anomaly_effects.get("signal_loss", 0) > 0.5:
                mission_status = "Limited"

            records.append({
                "satellite_id": profile.satellite_id,
                "timestamp": ts,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "altitude_km": round(altitude, 4),
                "velocity_kms": round(velocity, 4),
                "orbit_number": orbit_num,
                "battery_pct": round(battery, 2),
                "solar_voltage_v": round(solar_voltage, 2),
                "current_a": round(current, 2),
                "temperature_c": round(temperature, 2),
                "cpu_usage_pct": round(cpu, 2),
                "memory_usage_pct": round(memory, 2),
                "signal_strength_dbm": round(signal, 2),
                "radiation_level": round(radiation, 2),
                "gyro_x": round(gyro_x, 6),
                "gyro_y": round(gyro_y, 6),
                "gyro_z": round(gyro_z, 6),
                "accel_x": round(accel_x, 8),
                "accel_y": round(accel_y, 8),
                "accel_z": round(accel_z, 8),
                "sensor_status": sensor_status,
                "comm_status": comm_status,
                "mission_status": mission_status,
                "data_source": "simulated",
            })

        return records

    def _get_anomaly_effects(self, anomalies: Dict, index: int, total: int) -> Dict[str, float]:
        effects = {}
        for key, config in anomalies.items():
            start = config["start"]
            end = start + config["duration"]
            if start <= index < end:
                progress = (index - start) / max(1, config["duration"])
                severity = config["severity"]
                if config["type"] == "battery_degradation":
                    effects["battery_degradation"] = severity * progress
                elif config["type"] == "temperature_spike":
                    effects["temperature_spike"] = severity * (1 - abs(2 * progress - 1))
                elif config["type"] == "signal_loss":
                    effects["signal_loss"] = severity * (1 - abs(2 * progress - 1))
                elif config["type"] == "cpu_spike":
                    effects["cpu_spike"] = severity
                elif config["type"] == "memory_spike":
                    effects["memory_spike"] = severity
                elif config["type"] == "sensor_failure":
                    effects["sensor_failure"] = severity
        return effects

    def generate_normal_scenario(self, satellite_count: int = 1, readings: int = 500) -> pd.DataFrame:
        self._anomaly_configs.clear()
        return self.generate_telemetry(count=satellite_count, readings=readings)

    def generate_anomaly_scenario(self, satellite_count: int = 3, readings: int = 500) -> pd.DataFrame:
        self.generate_satellites(satellite_count)

        satellite_ids = list(self.satellites.keys())

        if len(satellite_ids) >= 1:
            self.add_anomaly_scenario(
                satellite_ids[0], "battery_degradation",
                start_index=int(readings * 0.3), duration=int(readings * 0.4), severity=0.8
            )

        if len(satellite_ids) >= 2:
            self.add_anomaly_scenario(
                satellite_ids[1], "temperature_spike",
                start_index=int(readings * 0.5), duration=int(readings * 0.15), severity=0.9
            )

        if len(satellite_ids) >= 3:
            self.add_anomaly_scenario(
                satellite_ids[2], "signal_loss",
                start_index=int(readings * 0.6), duration=int(readings * 0.2), severity=0.7
            )
            self.add_anomaly_scenario(
                satellite_ids[2], "sensor_failure",
                start_index=int(readings * 0.65), duration=int(readings * 0.15), severity=1.0
            )

        return self.generate_telemetry(count=satellite_count, readings=readings)

    def get_satellite_profiles_df(self) -> pd.DataFrame:
        records = []
        for sat in self.satellites.values():
            records.append({
                "satellite_id": sat.satellite_id,
                "name": sat.name,
                "mission_type": sat.mission_type,
                "orbit_type": sat.orbit_type,
                "altitude_km": sat.altitude_nominal,
                "inclination": sat.inclination,
                "period_minutes": sat.period_minutes,
            })
        return pd.DataFrame(records)
