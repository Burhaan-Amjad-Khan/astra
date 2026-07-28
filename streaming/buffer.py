"""ASTRA Real-Time Streaming Buffer - High-Frequency Multi-Satellite Ingestion"""

import asyncio
import time
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from utils.helpers import setup_logging

logger = setup_logging("astra.streaming.buffer")


@dataclass
class BufferConfig:
    max_batch_size: int = 1000
    flush_interval_ms: int = 500
    max_buffer_size: int = 50000
    enable_dedup: bool = True
    dedup_window_ms: int = 100
    store_callback: Optional[Callable] = None


class TelemetryBuffer:
    def __init__(self, config: Optional[BufferConfig] = None):
        self.config = config or BufferConfig()
        self._buffer: List[Dict] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._ingested_count: int = 0
        self._flushed_count: int = 0
        self._dropped_count: int = 0
        self._satellite_streams: Dict[str, datetime] = {}
        self._last_flush_time = time.monotonic()
        self._recent_keys: set = set()
        self._key_expiry: Dict[str, float] = {}

    async def start(self):
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"TelemetryBuffer started (batch={self.config.max_batch_size}, "
                     f"flush={self.config.flush_interval_ms}ms)")

    async def stop(self):
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush(force=True)
        logger.info(f"TelemetryBuffer stopped. Ingested: {self._ingested_count}, "
                     f"Flushed: {self._flushed_count}")

    async def ingest(self, records: List[Dict[str, Any]]) -> int:
        accepted = 0
        async with self._lock:
            for record in records:
                if not self._validate_record(record):
                    self._dropped_count += 1
                    continue

                if self.config.enable_dedup:
                    dedup_key = self._make_dedup_key(record)
                    now = time.monotonic()
                    if dedup_key in self._recent_keys:
                        expiry = self._key_expiry.get(dedup_key, 0)
                        if now < expiry:
                            self._dropped_count += 1
                            continue
                    self._recent_keys.add(dedup_key)
                    self._key_expiry[dedup_key] = now + self.config.dedup_window_ms / 1000

                if len(self._buffer) >= self.config.max_buffer_size:
                    self._dropped_count += 1
                    continue

                if "ingested_at" not in record:
                    record["ingested_at"] = datetime.now(timezone.utc)
                if "data_source" not in record:
                    record["data_source"] = "realtime"

                self._buffer.append(record)
                self._satellite_streams[record.get("satellite_id", "unknown")] = datetime.now(timezone.utc)
                self._ingested_count += 1
                accepted += 1

            if len(self._buffer) >= self.config.max_batch_size:
                await self._flush_locked()

        return accepted

    async def ingest_single(self, record: Dict[str, Any]) -> bool:
        result = await self.ingest([record])
        return result > 0

    async def _flush_loop(self):
        while self._running:
            await asyncio.sleep(self.config.flush_interval_ms / 1000)
            now = time.monotonic()
            if now - self._last_flush_time >= self.config.flush_interval_ms / 1000:
                await self._flush()

    async def _flush(self, force: bool = False):
        async with self._lock:
            await self._flush_locked(force)

    async def _flush_locked(self, force: bool = False):
        if not self._buffer:
            return
        if not force and len(self._buffer) < self.config.max_batch_size / 2:
            return

        batch = self._buffer[:]
        self._buffer.clear()
        self._last_flush_time = time.monotonic()

        try:
            if self.config.store_callback:
                await self.config.store_callback(batch)
            self._flushed_count += len(batch)
            logger.debug(f"Flushed {len(batch)} records to storage")
        except Exception as e:
            logger.error(f"Flush failed: {e}. Re-queuing {len(batch)} records.")
            self._buffer = batch + self._buffer

    def _validate_record(self, record: Dict) -> bool:
        required = ["satellite_id", "timestamp"]
        for field in required:
            if field not in record:
                return False
        if not isinstance(record.get("timestamp"), (str, datetime)):
            return False
        return True

    def _make_dedup_key(self, record: Dict) -> str:
        sat_id = record.get("satellite_id", "?")
        ts = str(record.get("timestamp", ""))
        return f"{sat_id}:{ts}"

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self._buffer),
            "ingested_total": self._ingested_count,
            "flushed_total": self._flushed_count,
            "dropped_total": self._dropped_count,
            "active_streams": len(self._satellite_streams),
            "satellite_ids": list(self._satellite_streams.keys())[-20:],
            "buffer_pct": round(len(self._buffer) / max(1, self.config.max_buffer_size) * 100, 1),
        }

    def get_latest_values(self, satellite_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
        latest = {}
        async def _get():
            async with self._lock:
                ids_to_check = set(satellite_ids) if satellite_ids else None
                for record in reversed(self._buffer):
                    sid = record.get("satellite_id")
                    if ids_to_check and sid not in ids_to_check:
                        continue
                    if sid and sid not in latest:
                        latest[sid] = record
                    if ids_to_check and len(latest) >= len(ids_to_check):
                        break
            return latest

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(_get(), loop)
                return future.result(timeout=2)
        except:
            pass
        return latest
