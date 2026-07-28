"""ASTRA - ISRO Mission Control Dashboard"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import time
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DASHBOARD_CONFIG
from simulator.generator import TelemetrySimulator
from validation.validator import ValidationEngine
from analytics.engine import AnalyticsEngine
from health.scorer import HealthScorer
from anomaly.detector import AnomalyDetector
from explanation.explainer import ExplanationEngine
from reports.generator import ReportGenerator
from visualization.charts import (
    TimeSeriesCharts, ComparisonCharts, DistributionCharts,
    RelationshipCharts, CircularCharts, StatusCharts, MissionCharts,
)
from utils.helpers import setup_logging, health_category

logger = setup_logging("astra.dashboard")

st.set_page_config(
    page_title="ASTRA | ISRO Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SATELLITE_REGISTRY_FILE = Path(__file__).resolve().parent.parent / "data" / "satellite_registry.json"

ORBIT_TYPES = ["LEO", "MEO", "GEO", "SSO", "HEO"]
MISSION_TYPES = ["Earth Observation", "Communications", "Navigation",
                 "Scientific", "Weather", "Reconnaissance", "Technology Demo"]
STATUS_OPTIONS = ["Pre-Launch", "Active", "Standby", "Degraded", "Decommissioned"]


@st.cache_resource
def init_engines():
    return {
        "simulator": TelemetrySimulator(),
        "validator": ValidationEngine(),
        "analytics": AnalyticsEngine(),
        "health": HealthScorer(),
        "anomaly": AnomalyDetector(),
        "explainer": ExplanationEngine(),
        "reporter": ReportGenerator(),
    }


def load_satellite_registry():
    if SATELLITE_REGISTRY_FILE.exists():
        with open(SATELLITE_REGISTRY_FILE, "r") as f:
            return json.load(f)
    default = []
    for i in range(5):
        default.append({
            "satellite_id": f"ISRO-SAT-{i+1:03d}",
            "name": f"ISRO-Mission-{i+1}",
            "mission_type": MISSION_TYPES[i % len(MISSION_TYPES)],
            "orbit_type": ORBIT_TYPES[i % len(ORBIT_TYPES)],
            "status": "Active",
            "registered_at": datetime.utcnow().isoformat(),
            "description": f"ISRO satellite mission {i+1}",
            "altitude_km": np.random.choice([450, 600, 800, 1200, 35786]),
            "launch_date": (datetime.utcnow() - timedelta(days=np.random.randint(30, 1000))).date().isoformat(),
        })
    save_satellite_registry(default)
    return default


def save_satellite_registry(registry):
    SATELLITE_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SATELLITE_REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2, default=str)


def generate_data():
    engines = init_engines()
    registry = load_satellite_registry()
    active_sats = [s for s in registry if s["status"] == "Active"]
    count = min(len(active_sats), 10) if active_sats else 5

    with st.spinner("Initializing mission telemetry..."):
        st.session_state.df = engines["simulator"].generate_anomaly_scenario(
            satellite_count=count, readings=500
        )
        st.session_state.profiles = engines["simulator"].get_satellite_profiles_df()
        st.session_state.registry = registry
        st.session_state.data_ready = True


engines = init_engines()

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False
    st.session_state.df = None
    st.session_state.profiles = None
    st.session_state.registry = load_satellite_registry()
    st.session_state.page_history = []
    st.session_state.current_page = "Mission Overview"
    st.session_state.interface_mode = "Engineer"

if "page_history" not in st.session_state:
    st.session_state.page_history = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Mission Overview"
if "registry" not in st.session_state:
    st.session_state.registry = load_satellite_registry()
if "interface_mode" not in st.session_state:
    st.session_state.interface_mode = "Engineer"


def navigate_to(page):
    st.session_state.page_history.append(st.session_state.current_page)
    st.session_state.current_page = page


def go_back():
    if st.session_state.page_history:
        st.session_state.current_page = st.session_state.page_history.pop()


def render_header():
    cols = st.columns([1, 8, 1])
    with cols[0]:
        st.markdown("### 🛰️")
    with cols[1]:
        st.markdown("""
        <div style="text-align:center;">
            <h2 style="color:#00CC96;margin-bottom:0;">ASTRA</h2>
            <p style="color:#888;font-size:14px;margin-top:0;">
                Advanced Satellite Telemetry & Real-time Analytics | ISRO Mission Control
            </p>
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"<div style='text-align:right;padding-top:20px;color:#666;'>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>", unsafe_allow_html=True)
    st.markdown("---")


def render_status_bar(df):
    if df is None:
        return
    satellite_ids = sorted(df["satellite_id"].unique())
    fleet_health = []
    for sid in satellite_ids[:20]:
        sdf = df[df["satellite_id"] == sid]
        health = engines["health"].compute_health(sdf)
        fleet_health.append({"satellite_id": sid, "score": health["overall_score"], "status": health["status"]})

    excellent = sum(1 for h in fleet_health if h["score"] >= 90)
    good = sum(1 for h in fleet_health if 70 <= h["score"] < 90)
    warning = sum(1 for h in fleet_health if 40 <= h["score"] < 70)
    critical = sum(1 for h in fleet_health if h["score"] < 40)

    cols = st.columns(7)
    cols[0].metric("🛰️ Fleet", len(satellite_ids))
    cols[1].metric("🟢 Excellent", excellent)
    cols[2].metric("🔵 Good", good)
    cols[3].metric("🟠 Warning", warning)
    cols[4].metric("🔴 Critical", critical)
    avg_health = np.mean([h["score"] for h in fleet_health]) if fleet_health else 0
    cols[5].metric("📊 Avg Health", f"{avg_health:.0f}%")
    cols[6].metric("📡 Records", f"{len(df):,}")


def render_navigation():
    pages = [
        ("📋", "Mission Overview"),
        ("📡", "Live Monitor"),
        ("🛰️", "Satellite Details"),
        ("📊", "Analytics"),
        ("⚠️", "Anomaly Detection"),
        ("🤖", "AI Insights"),
        ("📝", "Reports"),
        ("🔧", "Register Satellite"),
    ]

    cols = st.columns(len(pages))
    for i, (icon, name) in enumerate(pages):
        with cols[i]:
            is_current = name == st.session_state.current_page
            if st.button(f"{icon} {name}", key=f"nav_{name}", use_container_width=True,
                         type="primary" if is_current else "secondary"):
                if not is_current:
                    navigate_to(name)
                st.rerun()


# ── MAIN APP ──
render_header()

# ── Sidebar ──
with st.sidebar:
    st.markdown("## 🛰️ ASTRA")
    st.markdown("---")

    interface_mode = st.radio(
        "Interface Mode",
        ["Engineer", "Scientist", "Student"],
        index=["Engineer", "Scientist", "Student"].index(st.session_state.interface_mode),
        key="mode_selector",
        help="Engineer: Full technical details | Scientist: Research analytics | Student: Simple explanations",
    )
    if interface_mode != st.session_state.interface_mode:
        st.session_state.interface_mode = interface_mode

    st.markdown("---")

    if st.session_state.data_ready:
        df = st.session_state.df
        satellite_ids = sorted(df["satellite_id"].unique())
        st.markdown(f"**Fleet:** {len(satellite_ids)} sats")
        st.markdown(f"**Records:** {len(df):,}")
        st.markdown(f"**Mode:** {st.session_state.interface_mode}")

        st.markdown("---")
        if st.button("🔄 Regenerate Data", use_container_width=True):
            st.cache_resource.clear()
            st.session_state.data_ready = False
            st.rerun()

if not st.session_state.data_ready:
    st.markdown("""
    <div style="text-align:center;padding:50px;">
        <h3>Welcome to ASTRA Mission Control</h3>
        <p>Initialize the system to begin monitoring satellite telemetry.</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🚀 Initialize Mission Control", type="primary", use_container_width=True):
            generate_data()
            st.rerun()
    with col2:
        sat_count = st.number_input("Fleet Size", 1, 50, 10)
        if st.button("⚙️ Custom Initialize", use_container_width=True):
            with st.spinner(f"Initializing {sat_count} satellite fleet..."):
                st.session_state.df = engines["simulator"].generate_anomaly_scenario(
                    satellite_count=sat_count, readings=300
                )
                st.session_state.profiles = engines["simulator"].get_satellite_profiles_df()
                st.session_state.data_ready = True
            st.rerun()

    st.markdown("---")
    st.markdown("### Registered Satellites")
    registry_df = pd.DataFrame(st.session_state.registry)
    if not registry_df.empty:
        st.dataframe(registry_df[["satellite_id", "name", "mission_type", "orbit_type", "status"]],
                     use_container_width=True, hide_index=True)

else:
    df = st.session_state.df
    satellite_ids = sorted(df["satellite_id"].unique())
    render_status_bar(df)
    render_navigation()
    st.markdown("---")

    page = st.session_state.current_page

    # ── Back button ──
    if st.session_state.page_history:
        if st.button("⬅ Back", key="back_btn"):
            go_back()
            st.rerun()

    # ── MISSION OVERVIEW ──
    if page == "Mission Overview":
        st.title("📋 Mission Overview")

        fleet_health = []
        excellent = good = warning = critical = 0
        total_score = 0

        with st.spinner("Computing fleet health status..."):
            for sid in satellite_ids:
                sdf = df[df["satellite_id"] == sid]
                health = engines["health"].compute_health(sdf)
                score = health["overall_score"]
                total_score += score
                fleet_health.append({
                    "satellite_id": sid,
                    "score": score,
                    "status": health["status"],
                    "battery": health["metric_scores"].get("battery_pct", {}).get("value", 0),
                    "temperature": health["metric_scores"].get("temperature_c", {}).get("value", 0),
                })
                if score >= 90: excellent += 1
                elif score >= 70: good += 1
                elif score >= 40: warning += 1
                else: critical += 1

        n = len(satellite_ids)
        avg_health = round(total_score / n, 1) if n > 0 else 0

        st.markdown("### Fleet Health Dashboard")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.plotly_chart(
                StatusCharts.gauge_chart(avg_health, "Fleet Average Health"),
                use_container_width=True,
            )
        with col2:
            dist_data = {"Excellent": excellent, "Good": good, "Warning": warning, "Critical": critical}
            st.plotly_chart(
                CircularCharts.donut_chart(dist_data, "Health Distribution", f"{avg_health}%"),
                use_container_width=True,
            )
        with col3:
            health_scores_map = {h["satellite_id"]: h["score"] for h in fleet_health[:10]}
            st.plotly_chart(
                StatusCharts.progress_bars(health_scores_map, "Top 10 Health Scores"),
                use_container_width=True,
            )
        with col4:
            st.markdown("### Quick Stats")
            st.metric("Total Fleet", n)
            st.metric("Average Health", f"{avg_health}%")
            st.metric("Active Missions", excellent + good)
            st.metric("Attention Needed", warning + critical)

        st.markdown("### Fleet Telemetry Table")
        fleet_df = pd.DataFrame(fleet_health)
        st.dataframe(fleet_df, use_container_width=True, hide_index=True)

    # ── LIVE MONITOR ──
    elif page == "Live Monitor":
        st.title("📡 Live Telemetry Monitor")

        import httpx

        col1, col2, col3, col4 = st.columns(4)
        with col1: stream_sats = st.number_input("Satellites", 1, 50, 5)
        with col2: stream_interval = st.number_input("Interval (ms)", 50, 5000, 200, 50)
        with col3: stream_batch = st.number_input("Batch Size", 10, 500, 100, 10)
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            start_btn = st.button("▶ Start Stream", type="primary", use_container_width=True)
            stop_btn = st.button("⏹ Stop Stream", use_container_width=True)

        if start_btn:
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post("http://localhost:8000/api/stream/start",
                                       params={"satellites": stream_sats, "interval_ms": stream_interval,
                                                "batch_size": stream_batch, "include_anomalies": True})
                    if resp.status_code == 200:
                        st.success(resp.json().get("message", "Stream started"))
                        st.session_state.stream_active = True
                    else:
                        st.error(f"Failed: {resp.text}")
            except Exception:
                st.warning("API server not available. Standalone mode.")

        if stop_btn:
            try:
                with httpx.Client(timeout=10) as client:
                    client.post("http://localhost:8000/api/stream/stop")
            except Exception:
                pass
            st.session_state.stream_active = False
            st.info("Stream stopped")

        if st.session_state.get("stream_active", False):
            st.info("Live telemetry streaming active. Data is being ingested into the database.")
            status_ph = st.empty()
            for i in range(10):
                try:
                    with httpx.Client(timeout=3) as client:
                        resp = client.get("http://localhost:8000/api/stream/status")
                        if resp.status_code == 200:
                            stats = resp.json()
                            cols = st.columns(5)
                            cols[0].metric("Buffer", stats.get("buffer_size", 0))
                            cols[1].metric("Ingested", stats.get("ingested_total", 0))
                            cols[2].metric("Flushed", stats.get("flushed_total", 0))
                            cols[3].metric("Dropped", stats.get("dropped_total", 0))
                            cols[4].metric("WS Clients", stats.get("ws_clients", 0))
                except Exception:
                    pass
                time.sleep(1)

    # ── SATELLITE DETAILS ──
    elif page == "Satellite Details":
        st.title(f"🛰️ Satellite Details: {st.session_state.get('selected_sat', satellite_ids[0])}")

        selected_sat = st.selectbox("Select Satellite", satellite_ids, key="sat_selector")
        st.session_state.selected_sat = selected_sat

        sat_df = df[df["satellite_id"] == selected_sat].copy()
        health = engines["health"].compute_health(sat_df)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### Health Score: {health['overall_score']:.1f}/100 — {health['status']}")
        with col2:
            st.markdown(f"**Records:** {len(sat_df)}")
            st.markdown(f"**From:** {sat_df['timestamp'].min()}")
        with col3:
            st.plotly_chart(StatusCharts.health_gauge(health["overall_score"], selected_sat),
                            use_container_width=True)

        tabs = st.tabs(["Power & Thermal", "Communications", "Navigation & Orbit", "Raw Data"])
        with tabs[0]:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(TimeSeriesCharts.line_chart(sat_df, "battery_pct", "Battery Level", selected_sat),
                                use_container_width=True)
            with c2:
                st.plotly_chart(TimeSeriesCharts.line_chart(sat_df, "temperature_c", "Temperature", selected_sat),
                                use_container_width=True)
            st.plotly_chart(TimeSeriesCharts.multi_line_chart(
                sat_df, ["solar_voltage_v", "current_a"], "Solar Power System", selected_sat),
                use_container_width=True)
        with tabs[1]:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(TimeSeriesCharts.line_chart(sat_df, "signal_strength_dbm", "Signal Strength", selected_sat),
                                use_container_width=True)
            with c2:
                st.plotly_chart(TimeSeriesCharts.area_chart(sat_df, "cpu_usage_pct", "CPU Usage", selected_sat),
                                use_container_width=True)
            st.plotly_chart(TimeSeriesCharts.line_chart(sat_df, "memory_usage_pct", "Memory Usage", selected_sat),
                            use_container_width=True)
        with tabs[2]:
            st.plotly_chart(MissionCharts.ground_track(sat_df, selected_sat), use_container_width=True)
            st.plotly_chart(TimeSeriesCharts.multi_line_chart(
                sat_df, ["altitude_km", "velocity_kms"], "Orbit Parameters", selected_sat),
                use_container_width=True)
        with tabs[3]:
            st.dataframe(sat_df.describe(), use_container_width=True)

    # ── ANALYTICS ──
    elif page == "Analytics":
        selected_sat = st.session_state.get("selected_sat", satellite_ids[0])
        selected_sat = st.selectbox("Select Satellite", satellite_ids, key="analytics_sat")
        sat_df = df[df["satellite_id"] == selected_sat]

        st.title(f"📊 Analytics: {selected_sat}")
        stats = engines["analytics"].compute_statistics(sat_df)
        correlation = engines["analytics"].compute_correlation(sat_df)
        relationships = engines["analytics"].analyze_relationships(sat_df)

        st.markdown("### Statistical Summary")
        stats_data = []
        for col_name, col_stats in stats.get("columns", {}).items():
            stats_data.append({"Metric": col_name, "Mean": f"{col_stats.mean:.2f}",
                               "Std Dev": f"{col_stats.std_dev:.2f}", "Min": f"{col_stats.min:.2f}",
                               "Max": f"{col_stats.max:.2f}", "Skewness": f"{col_stats.skewness:.2f}"})
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(DistributionCharts.histogram(sat_df, "battery_pct", "Battery Distribution"),
                            use_container_width=True)
        with c2:
            st.plotly_chart(DistributionCharts.histogram(sat_df, "temperature_c", "Temperature Distribution"),
                            use_container_width=True)

        if not correlation.empty:
            st.plotly_chart(RelationshipCharts.correlation_heatmap(correlation), use_container_width=True)

        st.markdown("### Key Relationships")
        for rel in relationships[:6]:
            st.metric(rel["name"], f"r = {rel['correlation']:.3f}", delta=f"{rel['strength']} {rel['direction']}")

    # ── ANOMALY DETECTION ──
    elif page == "Anomaly Detection":
        selected_sat = st.session_state.get("selected_sat", satellite_ids[0])
        selected_sat = st.selectbox("Select Satellite", satellite_ids, key="anomaly_sat")
        sat_df = df[df["satellite_id"] == selected_sat]

        st.title(f"⚠️ Anomaly Detection: {selected_sat}")
        analysis_df = engines["anomaly"].fit_detect(sat_df)
        anomalies = engines["anomaly"].classify_anomalies(analysis_df)
        anomaly_summary = engines["anomaly"].get_anomaly_summary(analysis_df, selected_sat)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Anomalies", len(anomalies))
        c2.metric("ML Anomaly %", f"{anomaly_summary.get('ml_anomaly_pct', 0):.1f}%")
        c3.metric("Severity", anomaly_summary.get("severity", "None"))
        c4.metric("Records", len(analysis_df))

        if anomalies:
            anomaly_df = pd.DataFrame(anomalies)
            st.dataframe(anomaly_df[["type", "timestamp", "metric", "value", "unit", "severity"]],
                         use_container_width=True, hide_index=True)

    # ── AI INSIGHTS ──
    elif page == "AI Insights":
        selected_sat = st.session_state.get("selected_sat", satellite_ids[0])
        selected_sat = st.selectbox("Select Satellite", satellite_ids, key="insight_sat")
        sat_df = df[df["satellite_id"] == selected_sat]

        st.title(f"🤖 AI Insights: {selected_sat}")
        health = engines["health"].compute_health(sat_df)
        anomaly_summary = engines["anomaly"].get_anomaly_summary(
            engines["anomaly"].fit_detect(sat_df), selected_sat)
        stats = engines["analytics"].compute_statistics(sat_df)
        trends = engines["analytics"].time_series_analysis(sat_df).get("trends", {})
        relationships = engines["analytics"].analyze_relationships(sat_df)

        explanation_data = {
            "satellite_id": selected_sat,
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": health["overall_score"],
            "overall_score": health["overall_score"],
            "metric_scores": health["metric_scores"],
            "metrics": health["metric_scores"],
            "statistics": stats.get("summary", {}),
            "stats": stats.get("summary", {}),
            "trends": trends,
            "correlations": relationships,
            "relationships": relationships,
            "anomalies": anomaly_summary,
            "anomaly_summary": anomaly_summary,
            "recommendations": health["recommendations"],
        }

        t1, t2, t3 = st.tabs(["Engineer View", "Scientist View", "Student View"])
        mode_idx = {"Engineer": 0, "Scientist": 1, "Student": 2}
        default_tab = mode_idx.get(st.session_state.interface_mode, 0)
        with t1:
            if default_tab == 0 or st.session_state.get("_tab_clicked"):
                st.markdown(f"**Current Mode: Engineer** (change in sidebar)")
                st.code(engines["explainer"].explain(explanation_data, "engineer"))
        with t2:
            if default_tab == 1 or st.session_state.get("_tab_clicked"):
                st.markdown(f"**Current Mode: Scientist** (change in sidebar)")
                st.code(engines["explainer"].explain(explanation_data, "scientist"))
        with t3:
            if default_tab == 2 or st.session_state.get("_tab_clicked"):
                st.markdown(f"**Current Mode: Student** (change in sidebar)")
                st.markdown(engines["explainer"].explain(explanation_data, "student").replace("\n", "\n\n"))

    # ── REPORTS ──
    elif page == "Reports":
        selected_sat = st.session_state.get("selected_sat", satellite_ids[0])
        selected_sat = st.selectbox("Select Satellite", satellite_ids, key="report_sat")
        sat_df = df[df["satellite_id"] == selected_sat]

        st.title(f"📝 Reports: {selected_sat}")
        c1, c2, c3 = st.columns(3)
        with c1:
            csv_data = engines["reporter"].get_csv_bytes(sat_df)
            st.download_button("📥 Download CSV", csv_data, f"{selected_sat}_telemetry.csv",
                               "text/csv", use_container_width=True)
        with c2:
            stats_df = pd.DataFrame(engines["analytics"].compute_statistics(sat_df).get("summary", {})).T
            excel_bytes = engines["reporter"].get_excel_bytes({"Telemetry": sat_df, "Statistics": stats_df})
            st.download_button("📥 Download Excel", excel_bytes, f"{selected_sat}_report.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        with c3:
            health = engines["health"].compute_health(sat_df)
            stats = engines["analytics"].compute_statistics(sat_df)
            report = engines["reporter"].generate_telemetry_report_data(
                selected_sat, sat_df, stats, health, {}, "")
            json_bytes = engines["reporter"].get_json_bytes(report)
            st.download_button("📥 Download JSON", json_bytes, f"{selected_sat}_report.json",
                               "application/json", use_container_width=True)

        st.markdown("### Data Preview")
        st.dataframe(sat_df.head(50), use_container_width=True, hide_index=True)

    # ── REGISTER SATELLITE ──
    elif page == "Register Satellite":
        st.title("🔧 Satellite Registration & Management")

        tab_reg, tab_list = st.tabs(["Register New Satellite", "Manage Fleet"])

        with tab_reg:
            st.markdown("### Register a New Satellite")
            with st.form("satellite_registration_form"):
                c1, c2 = st.columns(2)
                with c1:
                    sat_id = st.text_input("Satellite ID", placeholder="e.g. ISRO-SAT-006")
                    sat_name = st.text_input("Satellite Name", placeholder="e.g. Cartosat-4")
                    mission_type = st.selectbox("Mission Type", MISSION_TYPES)
                    orbit_type = st.selectbox("Orbit Type", ORBIT_TYPES)
                with c2:
                    status = st.selectbox("Status", STATUS_OPTIONS)
                    altitude = st.number_input("Nominal Altitude (km)", 200, 40000, 600)
                    launch_date = st.date_input("Launch Date")
                    description = st.text_area("Description", placeholder="Mission description...")

                submitted = st.form_submit_button("✅ Register Satellite", type="primary", use_container_width=True)
                if submitted:
                    if not sat_id or not sat_name:
                        st.error("Satellite ID and Name are required.")
                    else:
                        registry = st.session_state.registry
                        if any(s["satellite_id"] == sat_id for s in registry):
                            st.error(f"Satellite '{sat_id}' already exists.")
                        else:
                            new_sat = {
                                "satellite_id": sat_id,
                                "name": sat_name,
                                "mission_type": mission_type,
                                "orbit_type": orbit_type,
                                "status": status,
                                "altitude_km": altitude,
                                "launch_date": launch_date.isoformat(),
                                "description": description,
                                "registered_at": datetime.utcnow().isoformat(),
                            }
                            registry.append(new_sat)
                            save_satellite_registry(registry)
                            st.session_state.registry = registry
                            st.success(f"Satellite '{sat_id}' registered successfully!")
                            st.rerun()

        with tab_list:
            st.markdown("### Registered Satellite Fleet")
            registry = st.session_state.registry
            if registry:
                reg_df = pd.DataFrame(registry)
                st.dataframe(reg_df[["satellite_id", "name", "mission_type", "orbit_type",
                                     "altitude_km", "status", "launch_date"]],
                             use_container_width=True, hide_index=True)

                st.markdown("### Update Satellite Status")
                col_sel, col_status = st.columns(2)
                with col_sel:
                    update_sat = st.selectbox("Satellite", [s["satellite_id"] for s in registry])
                with col_status:
                    new_status = st.selectbox("New Status", STATUS_OPTIONS)
                if st.button("🔄 Update Status"):
                    for s in registry:
                        if s["satellite_id"] == update_sat:
                            s["status"] = new_status
                            s["updated_at"] = datetime.utcnow().isoformat()
                    save_satellite_registry(registry)
                    st.session_state.registry = registry
                    st.success(f"Updated {update_sat} to {new_status}")
                    st.rerun()

                if st.button("🗑 Remove Satellite", type="secondary"):
                    registry = [s for s in registry if s["satellite_id"] != update_sat]
                    save_satellite_registry(registry)
                    st.session_state.registry = registry
                    st.warning(f"Removed {update_sat} from registry")
                    st.rerun()
            else:
                st.info("No satellites registered yet.")


# ── Footer ──
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#555;font-size:12px;'>"
    "ASTRA v1.0 | ISRO Mission Control | Satellite Telemetry Intelligence Platform | "
    f"Session: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    "</div>",
    unsafe_allow_html=True,
)
