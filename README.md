# ASTRA - Advanced Satellite Telemetry & Real-time Analytics

**ISRO Mission Control Grade** | Satellite Telemetry Intelligence Platform

> Processing, analyzing, visualizing, and explaining satellite telemetry data at scale.

[![GitHub](https://img.shields.io/badge/GitHub-Burhaan--Amjad--Khan%2Fastra-blue)](https://github.com/Burhaan-Amjad-Khan/astra)

## Architecture

```
ASTRA
 |
 |-- Data Ingestion Layer
 |-- Telemetry Validation Layer
 |-- Data Cleaning Layer
 |-- Storage Layer (DuckDB)
 |-- Analytics Engine
 |-- AI Intelligence Engine
 |-- Visualization Engine (22+ chart types)
 |-- Alert / Anomaly Detection Engine
 |-- Report Generator (CSV / Excel / JSON)
 |-- Dashboard Interface (Streamlit)
 |-- Telemetry Simulator
```

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### Run System Test

```bash
python main.py test
```

This validates all 7 engine modules and prints results.

### Start API Server

```bash
python main.py api
```

API available at http://localhost:8000 — Swagger docs at http://localhost:8000/docs

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

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API status |
| `POST /api/simulate` | Generate telemetry data |
| `GET /api/satellites` | List all satellites |
| `GET /api/telemetry/{id}` | Get telemetry records |
| `GET /api/validate/{id}` | Run data validation |
| `GET /api/analytics/{id}` | Compute statistics |
| `GET /api/health/{id}` | Health score |
| `GET /api/anomalies/{id}` | Anomaly detection |
| `GET /api/explain/{id}` | AI explanation |
| `GET /api/fleet/overview` | Fleet summary |
| `GET /api/export/csv/{id}` | CSV export |
| `GET /api/export/excel/{id}` | Excel export |
| `GET /api/export/json/{id}` | JSON report |

## Dashboard Pages

1. **Mission Overview** — Fleet health, satellite counts, health scores
2. **Satellite Details** — Telemetry graphs, metrics, ground track, 3D orbit
3. **Analytics** — Statistics, distributions, correlations, trends
4. **Anomaly Detection** — ML-based anomaly detection and visualization
5. **AI Insights** — Engineer, Scientist, and Student mode explanations
6. **Reports** — CSV, Excel, JSON export

## Interface Modes

- **Engineer Mode** — Full technical details with raw metrics and statistics
- **Scientist Mode** — Research-oriented analysis with distribution and correlation data
- **Student Mode** — Simplified explanations with plain language and visual indicators

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI |
| Dashboard | Streamlit |
| Database | DuckDB |
| Data Processing | Pandas, NumPy, SciPy |
| ML / AI | Scikit-learn (Isolation Forest) |
| Visualization | Plotly (22+ chart types) |
| Export | openpyxl (Excel), CSV, JSON |

## Project Structure

```
astra/
├── config/          # Configuration and settings
├── simulator/       # Telemetry data generator
├── validation/      # Data validation engine
├── analytics/       # Statistics, trends, correlations
├── health/          # Health scoring engine
├── anomaly/         # ML anomaly detection
├── visualization/   # 22+ chart types
├── explanation/     # AI explanation engine
├── reports/         # CSV/Excel/JSON export
├── api/             # FastAPI server
├── dashboard/       # Streamlit dashboard
├── storage/         # DuckDB database layer
├── utils/           # Helpers and logging
├── data/            # Database and exports
├── tests/           # Test suite
├── main.py          # Entry point
├── Dockerfile       # Docker build
└── docker-compose.yml
```

## Simulator Features

- Generates realistic orbital mechanics with proper Keplerian elements
- Eclipse-aware solar charging simulation
- Supports LEO, MEO, GEO, SSO, HEO orbit types
- Anomaly injection: battery degradation, temperature spikes, signal loss, sensor failure, CPU/memory overload
- Scalable from 1 to 5000+ satellites
- Cleanly separated from the analytics engine — real data can be connected without changes

## Connecting Real Satellite Data

The platform is designed with a clean separation between simulated and real data:

1. Feed real telemetry through the `POST /api/simulate` endpoint
2. Or insert directly into the DuckDB `telemetry` table
3. All analytics, health scoring, and anomaly detection work identically on real data
4. Set `data_source` field to `"live"` to distinguish from simulated data
