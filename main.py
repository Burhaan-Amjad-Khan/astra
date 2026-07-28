"""ASTRA - Advanced Satellite Telemetry & Real-time Analytics
Main entry point for launching the platform."""

import argparse
import sys
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import API_CONFIG


def run_api():
    print(f"[ASTRA] Starting API server on {API_CONFIG['host']}:{API_CONFIG['port']}")
    uvicorn.run(
        "api.server:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["reload"],
        log_level="info",
    )


def run_dashboard():
    import subprocess
    print("[ASTRA] Starting Streamlit dashboard on port 8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).resolve().parent / "dashboard" / "app.py"),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
    ])


def run_all():
    import subprocess
    import time

    print("[ASTRA] Starting all services...")

    api_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "api.server:app",
        "--host", API_CONFIG["host"],
        "--port", str(API_CONFIG["port"]),
    ])
    print(f"[ASTRA] API server started (PID: {api_proc.pid})")

    time.sleep(2)

    dash_proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).resolve().parent / "dashboard" / "app.py"),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
    ])
    print(f"[ASTRA] Dashboard started (PID: {dash_proc.pid})")
    print(f"[ASTRA] API: http://localhost:{API_CONFIG['port']}")
    print("[ASTRA] Dashboard: http://localhost:8501")

    try:
        api_proc.wait()
        dash_proc.wait()
    except KeyboardInterrupt:
        print("\n[ASTRA] Shutting down...")
        api_proc.terminate()
        dash_proc.terminate()
        api_proc.wait()
        dash_proc.wait()


def run_test():
    from simulator.generator import TelemetrySimulator
    from validation.validator import ValidationEngine
    from analytics.engine import AnalyticsEngine
    from health.scorer import HealthScorer
    from anomaly.detector import AnomalyDetector
    from explanation.explainer import ExplanationEngine

    print("=" * 60)
    print("ASTRA - System Test")
    print("=" * 60)

    print("\n[1/7] Telemetry Simulator...")
    sim = TelemetrySimulator()
    df = sim.generate_anomaly_scenario(satellite_count=3, readings=200)
    print(f"  Generated: {len(df)} records, {df['satellite_id'].nunique()} satellites")
    print(f"  Satellites: {sorted(df['satellite_id'].unique())}")

    print("\n[2/7] Data Validation...")
    validator = ValidationEngine()
    report = validator.validate(df)
    print(f"  Quality Score: {report['quality_score']}%")
    print(f"  Issues: {len(report.get('all_issues', []))}")

    print("\n[3/7] Analytics Engine...")
    analytics = AnalyticsEngine()
    sat_id = df["satellite_id"].unique()[0]
    sat_df = df[df["satellite_id"] == sat_id]
    stats = analytics.compute_statistics(sat_df)
    print(f"  Metrics analyzed: {len(stats.get('columns', {}))}")
    relationships = analytics.analyze_relationships(sat_df)
    for r in relationships[:3]:
        print(f"  {r['name']}: r={r['correlation']:.3f} ({r['strength']})")

    print("\n[4/7] Health Scoring...")
    health_scorer = HealthScorer()
    health = health_scorer.compute_health(sat_df)
    print(f"  Health Score: {health['overall_score']}/100 - {health['status']}")

    print("\n[5/7] Anomaly Detection...")
    anomaly_detector = AnomalyDetector()
    anomalies = anomaly_detector.classify_anomalies(sat_df)
    print(f"  Anomalies detected: {len(anomalies)}")

    print("\n[6/7] AI Explanation...")
    explainer = ExplanationEngine()
    explanation = explainer.explain({
        "satellite_id": sat_id,
        "health_score": health["overall_score"],
        "metric_scores": health["metric_scores"],
        "recommendations": health["recommendations"],
    }, "student")
    print(f"  Explanation: {explanation[:100]}...")

    print("\n[7/7] Storage...")
    from storage.database import TelemetryDatabase
    db = TelemetryDatabase()
    db.initialize()
    summary = db.get_summary_stats()
    print(f"  DB size: {summary.get('db_size', 'N/A')}")
    db.close()

    print("\n" + "=" * 60)
    print("All systems operational. ASTRA is ready for deployment.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASTRA Platform Launcher")
    parser.add_argument("command", nargs="?", default="test",
                        choices=["api", "dashboard", "all", "test"],
                        help="Service to launch")
    parser.add_argument("--port", type=int, default=8000, help="API port")

    args = parser.parse_args()

    if args.command == "api":
        run_api()
    elif args.command == "dashboard":
        run_dashboard()
    elif args.command == "all":
        run_all()
    else:
        run_test()
