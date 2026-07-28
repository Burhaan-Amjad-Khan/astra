# 🛰️ ASTRA — Advanced Satellite Telemetry & Real-time Analytics

**ISRO Mission Control Grade** | Satellite Telemetry Intelligence Platform

[![GitHub](https://img.shields.io/badge/GitHub-Burhaan--Amjad--Khan%2Fastra-blue)](https://github.com/Burhaan-Amjad-Khan/astra)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.140-teal)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.60-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A production-grade satellite telemetry intelligence platform that processes, validates, analyzes, visualizes, and explains satellite telemetry data from thousands of satellites simultaneously.

---

## 🎯 Features

### Core Capabilities
- **Realistic Telemetry Simulator** — Generates LEO/MEO/GEO/SSO/HEO orbit data with Keplerian mechanics, eclipse-aware solar charging, and anomaly injection
- **Data Validation Engine** — Auto-detects missing values, duplicates, format errors, range violations, timestamp gaps — produces Data Quality Score
- **Analytics Engine** — Mean, median, quartiles, skewness, kurtosis, trend analysis, correlation matrix, rate of change detection
- **Health Scoring System** — Weighted multi-metric scoring (Battery 25%, Temp 15%, Signal 15%, CPU 10%, Memory 10%, Radiation 10%, Solar 10%, Sensors 5%) — 0-100 scale
- **ML Anomaly Detection** — Isolation Forest + statistical threshold detection for temperature spikes, battery degradation, signal loss, CPU/memory overload, sensor failure
- **AI Explanation Engine** — Three modes: Engineer (technical), Scientist (research), Student (simple) — never invents values

### Real-Time Streaming
- **Sub-second Ingestion** — TelemetryBuffer with configurable batch size, flush interval, and deduplication
- **WebSocket Endpoints** — `/ws/ingest` for live data push, `/ws/live` for client subscriptions
- **Live Simulator** — Concurrent multi-satellite stream generator at configurable intervals (50ms+)
- **Batch & Single Ingest** — REST endpoints for high-frequency HTTP-based ingestion

### Visualization (22+ Chart Types)
| Category | Charts |
|----------|--------|
| Time Series | Line, Multi-Line, Area, Step |
| Comparison | Bar, Horizontal Bar, Grouped Bar, Stacked Bar, Satellite Comparison |
| Distribution | Histogram, Box Plot, Violin Plot |
| Relationship | Scatter, Bubble, Correlation Heatmap |
| Circular | Pie, Donut, Radar |
| Status | Gauge, Health Gauge, Progress Bars |
| Mission | Ground Track (Map), 3D Orbit Visualization |

### Dashboard (7 Pages)
1. **Mission Overview** — Fleet health gauges, distribution donut, progress bars, telemetry table
2. **Live Monitor** — Real-time stream control with status metrics
3. **Satellite Details** — Power/thermal, communications, navigation, orbit tabs
4. **Analytics** — Statistical summary, distributions, correlation heatmap, scatter plots
5. **Anomaly Detection** — ML + statistical anomaly reports with severity classification
6. **AI Insights** — Multi-mode explanations with health progress bars
7. **Reports** — CSV, Excel, JSON export with data preview

### Satellite Management
- **Registration Panel** — Register new satellites with mission type, orbit, altitude, launch date
- **Fleet Management** — Update status (Pre-Launch/Active/Standby/Degraded/Decommissioned), remove satellites
- **Persistent Registry** — JSON-based satellite registry

### Interface Modes
- **Engineer** — Full technical metrics, raw statistics, detailed anomaly reports
- **Scientist** — Research-oriented analytics with distributions and correlations
- **Student** — Simple language, color-coded status, actionable recommendations

---

## 🏗️ Architecture

```
ASTRA
 |
 |-- Streaming Layer (WebSocket + Buffer + Live Simulator)
 |-- Data Ingestion Layer (REST + WebSocket)
 |-- Telemetry Validation Layer
 |-- Data Cleaning Layer
 |-- Storage Layer (DuckDB + PostgreSQL-ready schema)
 |-- Analytics Engine (Statistics + Time Series + Correlation)
 |-- Health Scoring Engine (8-metric weighted scoring)
 |-- Anomaly Detection (Isolation Forest + Statistical)
 |-- AI Explanation Engine (3 modes)
 |-- Visualization Engine (22+ charts, Plotly)
 |-- Report Generator (CSV / Excel / JSON)
 |-- API Server (FastAPI, 20+ endpoints)
 |-- Dashboard (Streamlit, 7 pages)
 |-- Telemetry Simulator (5 orbit types)
 |-- Satellite Registry (JSON persistence)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### Install
```bash
git clone https://github.com/Burhaan-Amjad-Khan/astra.git
cd astra
pip install -r requirements.txt --break-system-packages
```

### System Test
```bash
python main.py test
```
Validates all 7 engine modules and prints results.

### Start API Server
```bash
python main.py api
```
API at http://localhost:8000 — Swagger docs at http://localhost:8000/docs

### Start Dashboard
```bash
python main.py dashboard
```
Dashboard at http://localhost:8501

### Start All Services
```bash
python main.py all
```

### Docker
```bash
docker compose up -d
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API status |
| `GET` | `/api/health` | Health check with buffer stats |
| `POST` | `/api/simulate` | Generate telemetry data |
| `GET` | `/api/satellites` | List all satellites |
| `GET` | `/api/telemetry/{id}` | Get telemetry records |
| `GET` | `/api/validate/{id}` | Run data validation |
| `GET` | `/api/analytics/{id}` | Compute statistics & correlations |
| `GET` | `/api/health/{id}` | Health score with recommendations |
| `GET` | `/api/anomalies/{id}` | ML anomaly detection report |
| `GET` | `/api/explain/{id}` | AI explanation (engineer/scientist/student) |
| `GET` | `/api/fleet/overview` | Fleet health summary |
| `POST` | `/api/stream/start` | Start live telemetry stream |
| `POST` | `/api/stream/stop` | Stop live stream |
| `GET` | `/api/stream/status` | Stream buffer stats |
| `GET` | `/api/stream/latest` | Latest values for satellites |
| `POST` | `/api/ingest/batch` | Batch HTTP ingestion |
| `POST` | `/api/ingest/single` | Single record ingestion |
| `GET` | `/api/export/csv/{id}` | CSV download |
| `GET` | `/api/export/excel/{id}` | Excel report download |
| `GET` | `/api/export/json/{id}` | JSON report download |
| `WS` | `/ws/ingest` | WebSocket data push |
| `WS` | `/ws/live` | WebSocket live feed subscription |

---

## 🛰️ Connecting Real Satellite Data

The platform maintains a clean separation between simulated and real data:

1. Feed real telemetry via `POST /api/ingest/batch` or `WS /ws/ingest`
2. Or insert directly into the DuckDB `telemetry` table
3. All analytics, health scoring, and anomaly detection work identically on real data
4. Set `data_source: "live"` to distinguish from simulated data

---

## 📁 Project Structure

```
astra/
├── api/server.py             # FastAPI (20+ endpoints + WebSocket)
├── dashboard/app.py           # Streamlit (7-page mission control)
├── simulator/generator.py     # Realistic telemetry simulator
├── streaming/
│   ├── buffer.py              # Async telemetry buffer with dedup
│   └── live_simulator.py      # Sub-second stream generator
├── validation/validator.py    # Data quality scoring engine
├── analytics/engine.py        # Statistics, trends, correlations
├── health/scorer.py           # Weighted 8-metric health scoring
├── anomaly/detector.py        # Isolation Forest + thresholds
├── explanation/explainer.py   # 3-mode AI explanations
├── visualization/charts.py    # 22+ Plotly chart types
├── reports/generator.py       # CSV, Excel, JSON export
├── storage/database.py        # DuckDB (PostgreSQL-ready)
├── config/settings.py         # Central configuration
├── utils/helpers.py           # Logging, formatting, utilities
├── main.py                    # Entry point (api/dashboard/all/test)
├── Dockerfile                 # Docker build
├── docker-compose.yml         # Multi-service deployment
└── requirements.txt           # Python dependencies
```

---

## 🔧 Configuration

All settings in `config/settings.py`:

- `SIMULATION_CONFIG` — Default satellite count, sampling interval, seed
- `VALIDATION_CONFIG` — Range thresholds for all metrics
- `HEALTH_CONFIG` — Weights for health score components
- `ANOMALY_CONFIG` — Isolation Forest contamination, statistical thresholds
- `VIZ_CONFIG` — Plotly theme, color palette, export format
- `API_CONFIG` — Host, port, workers
- `LOG_CONFIG` — Log level, format, file path

---

## 📊 Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11, FastAPI |
| Dashboard | Streamlit |
| Database | DuckDB |
| Data Processing | Pandas, NumPy, SciPy |
| ML / AI | Scikit-learn (Isolation Forest) |
| Visualization | Plotly (22+ chart types) |
| Real-time | WebSocket, asyncio |
| Export | openpyxl (Excel), JSON |
| Deployment | Docker, docker-compose |

---

## 🤝 Contributing

Contributions are welcome. Please open an issue or pull request on GitHub.

## 📄 License

MIT License

---

**Built for ISRO-grade satellite telemetry intelligence and analytics.**
