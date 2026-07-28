"""ASTRA Live Telemetry Stream Simulator - Sub-Second Real-Time Generator"""

import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from simulator.generator import TelemetrySimulator, SatelliteProfile
from utils.helpers import setup_logging

logger = setup_logging("astra.streaming.live")


@dataclass
class StreamConfig:
    satellites: int = 5
    interval_ms: int = 100
    duration_seconds: int = 0
    batch_size: int = 100
    include_anomalies: bool = True


class LiveTelemetryStream:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config or StreamConfig()
        self.simulator = TelemetrySimulator()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._generated_count = 0
        self._callback: Optional[Callable] = None

    async def start(self, callback: Callable[[List[Dict]], Any]) -> asyncio.Task:
        self._callback = callback
        self._running = True

        self.simulator.generate_satellites(self.config.satellites)
        logger.info(f"LiveStream started: {self.config.satellites} satellites, "
                     f"{self.config.interval_ms}ms interval")

        if self.config.include_anomalies:
            sat_ids = list(self.simulator.satellites.keys())
            for i, sid in enumerate(sat_ids):
                if i % 3 == 0:
                    self.simulator.add_anomaly_scenario(
                        sid, "battery_degradation", 200, 100, severity=np.random.uniform(0.3, 0.7))
                if i % 4 == 1:
                    self.simulator.add_anomaly_scenario(
                        sid, "temperature_spike", 400, 50, severity=np.random.uniform(0.5, 0.9))

        self._tasks = []
        for sat_id in self.simulator.satellites.keys():
            task = asyncio.create_task(self._stream_satellite(sat_id))
            self._tasks.append(task)

        monitor = asyncio.create_task(self._monitor())
        return monitor

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info(f"LiveStream stopped. Generated: {self._generated_count} records")

    async def _stream_satellite(self, satellite_id: str):
        profile = self.simulator.satellites[satellite_id]
        tick = 0
        orbit_period_readings = int(profile.period_minutes * 60 * 1000 / self.config.interval_ms)
        body_rate = 2 * np.pi / orbit_period_readings

        base_lat = np.random.uniform(-60, 60)
        base_lon = np.random.uniform(0, 360)
        lat_drift = np.random.uniform(-0.1, 0.1) / 1000
        lon_drift = np.random.uniform(-0.1, 0.1) / 1000

        battery = np.random.uniform(85, 95)
        signal_base = np.random.uniform(-50, -40)
        cpu_base = np.random.uniform(20, 35)
        memory_base = np.random.uniform(30, 45)
        radiation_base = np.random.uniform(15, 45)

        batch = []
        last_flush = datetime.now(timezone.utc)

        while self._running:
            try:
                now = datetime.now(timezone.utc)
                phase = tick * body_rate
                eclipse_factor = 0.5 * (1 + np.sin(phase))

                altitude = profile.altitude_nominal + np.random.normal(0, 0.3)
                velocity = 7.8 - (altitude - 300) * 0.0005 + np.random.normal(0, 0.01)

                lat = (base_lat + lat_drift * tick + 30 * np.sin(phase * 0.3)) % 180 - 90
                lon = (base_lon + lon_drift * tick + 60 * phase / (2 * np.pi)) % 360
                if lon > 180:
                    lon -= 360

                charge_rate = eclipse_factor * profile.solar_efficiency * 0.003
                discharge_rate = (1 - eclipse_factor) * 0.001
                battery += charge_rate - discharge_rate + np.random.normal(0, 0.2)
                battery = max(0, min(100, battery))

                solar_voltage = 32 * eclipse_factor * profile.solar_efficiency + np.random.normal(0, 0.3)
                solar_voltage = max(0, solar_voltage)
                current = solar_voltage / np.random.uniform(8, 12) + np.random.normal(0, 0.1)
                current = max(0, current)

                temperature = 25 + 15 * (1 - eclipse_factor) + np.random.normal(0, 1)
                cpu = cpu_base + 10 * np.sin(phase * 3) + np.random.normal(0, 1.5)
                cpu = max(0, min(100, cpu))
                memory = memory_base + 5 * np.sin(phase * 2) + np.random.normal(0, 1)
                memory = max(0, min(100, memory))
                signal = signal_base + 10 * np.sin(phase * 0.5) + np.random.normal(0, 1.5)
                signal = max(-120, min(0, signal))
                radiation = radiation_base + 20 * np.sin(phase * 0.1) + np.random.normal(0, 2)
                radiation = max(0, radiation)

                gyro_x = 0.1 * np.sin(phase) + np.random.normal(0, 0.008)
                gyro_y = 0.1 * np.cos(phase) + np.random.normal(0, 0.008)
                gyro_z = 0.05 * np.sin(phase * 2) + np.random.normal(0, 0.008)
                accel_x = 0.01 * np.sin(phase * 3) + np.random.normal(0, 0.0008)
                accel_y = 0.01 * np.cos(phase * 3) + np.random.normal(0, 0.0008)
                accel_z = 0.005 * np.sin(phase * 5) + np.random.normal(0, 0.0008)

                record = {
                    "satellite_id": satellite_id,
                    "timestamp": now.isoformat(),
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "altitude_km": round(altitude, 4),
                    "velocity_kms": round(velocity, 4),
                    "orbit_number": tick // orbit_period_readings + 1,
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
                    "sensor_status": 1,
                    "comm_status": 1 if signal > -100 else 0,
                    "mission_status": "Nominal",
                    "data_source": "realtime",
                    "stream_tick": tick,
                }
                batch.append(record)
                self._generated_count += 1
                tick += 1

                if len(batch) >= self.config.batch_size:
                    await self._callback(batch)
                    batch = []
                    last_flush = now

                await asyncio.sleep(self.config.interval_ms / 1000)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream error for {satellite_id}: {e}")
                await asyncio.sleep(1)

        if batch:
            await self._callback(batch)

    async def _monitor(self):
        while self._running:
            await asyncio.sleep(5)
            logger.debug(f"LiveStream stats: {self._generated_count} records generated")
