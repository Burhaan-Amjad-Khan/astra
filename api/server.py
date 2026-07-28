"""ASTRA FastAPI Backend Server"""

from fastapi import FastAPI, Query, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio
import json
import io
import pandas as pd
import time

from config.settings import API_CONFIG
from simulator.generator import TelemetrySimulator
from validation.validator import ValidationEngine
from analytics.engine import AnalyticsEngine
from health.scorer import HealthScorer
from anomaly.detector import AnomalyDetector
from explanation.explainer import ExplanationEngine
from reports.generator import ReportGenerator
from storage.database import TelemetryDatabase
from streaming.buffer import TelemetryBuffer, BufferConfig
from streaming.live_simulator import LiveTelemetryStream, StreamConfig
from utils.helpers import setup_logging

logger = setup_logging("astra.api")

app = FastAPI(
    title="ASTRA - Advanced Satellite Telemetry & Real-time Analytics",
    description="ISRO-grade Satellite Telemetry Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = TelemetrySimulator()
validator = ValidationEngine()
analytics = AnalyticsEngine()
health_scorer = HealthScorer()
anomaly_detector = AnomalyDetector()
explainer = ExplanationEngine()
reporter = ReportGenerator()
db = TelemetryDatabase()

async def _store_batch_in_db(batch: List[Dict[str, Any]]):
    if not batch:
        return
    try:
        df = pd.DataFrame(batch)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        db.insert_telemetry_batch(df)
    except Exception as e:
        logger.error(f"Batch store failed: {e}")

telemetry_buffer = TelemetryBuffer(BufferConfig(
    max_batch_size=1000,
    flush_interval_ms=500,
    store_callback=_store_batch_in_db,
))

live_stream: Optional[LiveTelemetryStream] = None
_ws_clients: List[WebSocket] = []
_ws_lock = asyncio.Lock()
_stream_monitor: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup():
    db.initialize()
    await telemetry_buffer.start()
    logger.info("ASTRA API server started with real-time streaming enabled")


@app.get("/")
async def root():
    return {
        "name": "ASTRA API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "streaming": telemetry_buffer.stats,
    }


@app.websocket("/ws/ingest")
async def websocket_ingest(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket ingest client connected")
    try:
        while True:
            data = await websocket.receive_json()
            records = data if isinstance(data, list) else [data]
            accepted = await telemetry_buffer.ingest(records)
            await websocket.send_json({
                "status": "ok",
                "accepted": accepted,
                "buffer_size": telemetry_buffer.stats["buffer_size"],
            })
    except WebSocketDisconnect:
        logger.info("WebSocket ingest client disconnected")
    except Exception as e:
        logger.error(f"WebSocket ingest error: {e}")


@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    await websocket.accept()
    async with _ws_lock:
        _ws_clients.append(websocket)
    logger.info(f"Live feed client connected ({len(_ws_clients)} total)")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _ws_lock:
            _ws_clients.remove(websocket)
        logger.info(f"Live feed client disconnected ({len(_ws_clients)} total)")


async def _broadcast_live(data: List[Dict[str, Any]]):
    if not _ws_clients:
        return
    payload = json.dumps({
        "type": "telemetry",
        "count": len(data),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "records": data[:50],
    })
    async with _ws_lock:
        disconnected = []
        for ws in _ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            _ws_clients.remove(ws)


@app.post("/api/stream/start")
async def start_live_stream(
    satellites: int = Query(5, ge=1, le=100),
    interval_ms: int = Query(100, ge=10, le=5000),
    batch_size: int = Query(100, ge=10, le=1000),
    include_anomalies: bool = Query(True),
):
    global live_stream, _stream_monitor
    if live_stream and live_stream._running:
        return {"status": "already_running", "message": "Stream is already active"}

    config = StreamConfig(
        satellites=satellites,
        interval_ms=interval_ms,
        batch_size=batch_size,
        include_anomalies=include_anomalies,
    )
    live_stream = LiveTelemetryStream(config)

    async def on_batch(batch):
        await _broadcast_live(batch)
        await telemetry_buffer.ingest(batch)

    _stream_monitor = await live_stream.start(on_batch)
    return {
        "status": "started",
        "satellites": satellites,
        "interval_ms": interval_ms,
        "batch_size": batch_size,
        "message": f"Live stream started: {satellites} satellites at {interval_ms}ms interval",
    }


@app.post("/api/stream/stop")
async def stop_live_stream():
    global live_stream
    if live_stream:
        await live_stream.stop()
        live_stream = None
        return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/api/stream/status")
async def stream_status():
    stats = telemetry_buffer.stats
    stats["stream_active"] = live_stream is not None and live_stream._running if live_stream else False
    stats["ws_clients"] = len(_ws_clients)
    return stats


@app.post("/api/ingest/batch")
async def ingest_batch(payload: Dict[str, Any]):
    records = payload.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No records provided")

    accepted = await telemetry_buffer.ingest(records)
    return {
        "status": "ok",
        "received": len(records),
        "accepted": accepted,
        "dropped": len(records) - accepted,
        "buffer_stats": telemetry_buffer.stats,
    }


@app.post("/api/ingest/single")
async def ingest_single(payload: Dict[str, Any]):
    required = ["satellite_id", "timestamp"]
    for field in required:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    accepted = await telemetry_buffer.ingest_single(payload)
    return {
        "status": "ok",
        "accepted": accepted,
        "satellite_id": payload.get("satellite_id"),
    }


@app.post("/api/simulate")
async def simulate(
    satellites: int = Query(10, ge=1, le=5000),
    readings: int = Query(500, ge=10, le=10000),
    scenario: str = Query("normal", pattern="^(normal|anomaly)$"),
):
    logger.info(f"Simulating {satellites} satellites, {readings} readings, scenario={scenario}")
    if scenario == "anomaly":
        df = simulator.generate_anomaly_scenario(satellite_count=satellites, readings=readings)
    else:
        df = simulator.generate_normal_scenario(satellite_count=satellites, readings=readings)

    profiles = simulator.get_satellite_profiles_df()
    record_count = len(df)

    try:
        db.insert_telemetry_batch(df)
    except Exception as e:
        logger.warning(f"Database insert failed: {e}")

    return {
        "status": "success",
        "satellites": satellites,
        "readings_per_satellite": readings,
        "total_records": record_count,
        "scenario": scenario,
        "satellite_ids": df["satellite_id"].unique().tolist(),
    }


@app.get("/api/satellites")
async def list_satellites():
    profiles = simulator.get_satellite_profiles_df()
    if profiles.empty:
        try:
            profiles = db.get_all_satellites()
        except Exception:
            simulator.generate_satellites(10)
            simulator.generate_normal_scenario(satellite_count=10, readings=100)
            profiles = simulator.get_satellite_profiles_df()

    return {"satellites": profiles.to_dict(orient="records"), "count": len(profiles)}


@app.get("/api/telemetry/{satellite_id}")
async def get_telemetry(
    satellite_id: str,
    limit: int = Query(500, ge=1, le=10000),
):
    try:
        df = db.get_satellite_telemetry(satellite_id, limit=limit)
    except Exception:
        simulator.generate_satellites(1)
        df = simulator.generate_normal_scenario(satellite_count=1, readings=limit)
        df = df[df["satellite_id"].isin(df["satellite_id"].unique()[:1])]

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No telemetry found for {satellite_id}")

    return {
        "satellite_id": satellite_id,
        "record_count": len(df),
        "telemetry": df.to_dict(orient="records"),
    }


@app.get("/api/validate/{satellite_id}")
async def validate_telemetry(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    report = validator.validate(df)
    return report


@app.get("/api/analytics/{satellite_id}")
async def get_analytics(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    stats = analytics.compute_statistics(df)
    correlation = analytics.compute_correlation(df)
    relationships = analytics.analyze_relationships(df)
    time_series = analytics.time_series_analysis(df)
    distributions = analytics.distribution_analysis(df)

    return {
        "satellite_id": satellite_id,
        "record_count": len(df),
        "statistics": {"summary": stats.get("summary", {})},
        "correlations": {
            "matrix": correlation.to_dict() if not correlation.empty else {},
            "relationships": relationships,
        },
        "time_series": {"trends": time_series.get("trends", {})},
        "distributions": distributions,
    }


@app.get("/api/health/{satellite_id}")
async def get_health(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    health = health_scorer.compute_health(df)

    return {
        "satellite_id": satellite_id,
        "health_score": health["overall_score"],
        "status": health["status"],
        "color": health.get("color", "#00CC96"),
        "metric_scores": health["metric_scores"],
        "recommendations": health["recommendations"],
    }


@app.get("/api/anomalies/{satellite_id}")
async def detect_anomalies(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    df = anomaly_detector.fit_detect(df)
    anomalies = anomaly_detector.classify_anomalies(df)
    summary = anomaly_detector.get_anomaly_summary(df, satellite_id)

    return {
        "satellite_id": satellite_id,
        "total_anomalies": len(anomalies),
        "ml_anomaly_pct": summary.get("ml_anomaly_pct", 0),
        "severity": summary.get("severity", "None"),
        "anomalies": anomalies,
        "summary": summary.get("summary", ""),
    }


@app.get("/api/explain/{satellite_id}")
async def explain_telemetry(
    satellite_id: str,
    mode: str = Query("engineer", pattern="^(engineer|scientist|student)$"),
):
    df = _get_or_generate_data(satellite_id)
    health = health_scorer.compute_health(df)
    analysis_df = anomaly_detector.fit_detect(df)
    anomaly_summary = anomaly_detector.get_anomaly_summary(analysis_df, satellite_id)
    stats = analytics.compute_statistics(df)
    trends = analytics.time_series_analysis(df).get("trends", {})
    correlations = analytics.analyze_relationships(df)

    explanation_data = {
        "satellite_id": satellite_id,
        "timestamp": datetime.utcnow().isoformat(),
        "health_score": health["overall_score"],
        "overall_score": health["overall_score"],
        "metric_scores": health["metric_scores"],
        "metrics": health["metric_scores"],
        "statistics": stats.get("summary", {}),
        "stats": stats.get("summary", {}),
        "trends": trends,
        "correlations": correlations,
        "relationships": correlations,
        "anomalies": anomaly_summary,
        "anomaly_summary": anomaly_summary,
        "recommendations": health["recommendations"],
    }

    explanation = explainer.explain(explanation_data, mode)
    return {
        "satellite_id": satellite_id,
        "mode": mode,
        "explanation": explanation,
    }


@app.get("/api/fleet/overview")
async def fleet_overview():
    try:
        profiles = db.get_all_satellites()
    except Exception:
        profiles = simulator.get_satellite_profiles_df()
        if profiles.empty:
            simulator.generate_satellites(10)
            simulator.generate_normal_scenario(satellite_count=10, readings=200)
            profiles = simulator.get_satellite_profiles_df()

    satellite_ids = profiles["satellite_id"].tolist() if not profiles.empty else []

    fleet_health = []
    anomaly_counts = {}
    total_health = 0
    excellent = good = warning = critical = 0

    for sid in satellite_ids[:50]:
        try:
            df = _get_or_generate_data(sid, 200)
            health = health_scorer.compute_health(df)
            score = health["overall_score"]
            total_health += score

            if score >= 90:
                excellent += 1
            elif score >= 70:
                good += 1
            elif score >= 40:
                warning += 1
            else:
                critical += 1

            fleet_health.append({
                "satellite_id": sid,
                "health_score": score,
                "status": health["status"],
            })
        except Exception as e:
            logger.warning(f"Health compute failed for {sid}: {e}")

    n = max(1, len(fleet_health))
    return {
        "total_satellites": len(satellite_ids),
        "analyzed": len(fleet_health),
        "excellent": excellent,
        "good": good,
        "warning": warning,
        "critical": critical,
        "average_health": round(total_health / n, 1),
        "satellites": fleet_health,
    }


@app.get("/api/export/csv/{satellite_id}")
async def export_csv(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    csv_data = reporter.get_csv_bytes(df)
    return StreamingResponse(
        io.BytesIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={satellite_id}_telemetry.csv"},
    )


@app.get("/api/export/excel/{satellite_id}")
async def export_excel(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    stats_df = pd.DataFrame(analytics.compute_statistics(df).get("summary", {})).T
    excel_data = reporter.get_excel_bytes({
        "Telemetry": df,
        "Statistics": stats_df,
    })
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={satellite_id}_report.xlsx"},
    )


@app.get("/api/export/json/{satellite_id}")
async def export_json(satellite_id: str):
    df = _get_or_generate_data(satellite_id)
    health = health_scorer.compute_health(df)
    stats = analytics.compute_statistics(df)
    anomaly_summary = anomaly_detector.get_anomaly_summary(df, satellite_id)

    report_data = reporter.generate_telemetry_report_data(
        satellite_id, df, stats, health, anomaly_summary, ""
    )
    json_data = reporter.get_json_bytes(report_data)
    return StreamingResponse(
        io.BytesIO(json_data),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={satellite_id}_report.json"},
    )


def _get_or_generate_data(satellite_id: str, limit: int = 500) -> pd.DataFrame:
    df = pd.DataFrame()
    try:
        df = db.get_satellite_telemetry(satellite_id, limit=limit)
    except Exception:
        pass

    if not df.empty:
        return df

    simulator.generate_satellites(1)
    df = simulator.generate_normal_scenario(satellite_count=1, readings=limit)

    matched = df[df["satellite_id"] == satellite_id]
    if matched.empty:
        df["satellite_id"] = satellite_id
    return df


@app.get("/api/stream/latest")
async def get_latest_values(satellite_ids: Optional[str] = Query(None)):
    ids = satellite_ids.split(",") if satellite_ids else None
    latest = telemetry_buffer.get_latest_values(ids)
    return {
        "satellites": latest,
        "count": len(latest),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_CONFIG["host"], port=API_CONFIG["port"], reload=API_CONFIG["reload"])
