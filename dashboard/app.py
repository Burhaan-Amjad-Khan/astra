"""ASTRA Streamlit Dashboard - Main Entry Point"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import time
from pathlib import Path

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
    page_title=DASHBOARD_CONFIG["page_title"],
    page_icon=DASHBOARD_CONFIG["page_icon"],
    layout=DASHBOARD_CONFIG["layout"],
    initial_sidebar_state="expanded",
)


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


def generate_data():
    engines = init_engines()
    with st.spinner("Generating telemetry data..."):
        st.session_state.df = engines["simulator"].generate_anomaly_scenario(
            satellite_count=10, readings=500
        )
        st.session_state.profiles = engines["simulator"].get_satellite_profiles_df()
        st.session_state.data_ready = True


engines = init_engines()

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False
    st.session_state.df = None
    st.session_state.profiles = None
    st.session_state.mode = "Engineer"

st.sidebar.title("ASTRA")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Interface Mode",
    ["Engineer", "Scientist", "Student"],
    index=0,
    key="mode_select",
)

st.sidebar.markdown("---")

if not st.session_state.data_ready:
    st.sidebar.warning("No data loaded")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Quick Demo (10 sats)", use_container_width=True):
            generate_data()
            st.rerun()
    with col2:
        sat_count = st.sidebar.number_input("Count", 1, 100, 10, key="custom_sat_count")
        if st.button("Custom Generate", use_container_width=True):
            with st.spinner(f"Generating {sat_count} satellites..."):
                st.session_state.df = engines["simulator"].generate_anomaly_scenario(
                    satellite_count=sat_count, readings=300
                )
                st.session_state.profiles = engines["simulator"].get_satellite_profiles_df()
                st.session_state.data_ready = True
            st.rerun()

# ── Data ready: main dashboard ──
if st.session_state.data_ready:
    df = st.session_state.df
    profiles = st.session_state.profiles
    satellite_ids = sorted(df["satellite_id"].unique())

    st.sidebar.markdown("### Satellite Selection")
    selected_sat = st.sidebar.selectbox("Select Satellite", satellite_ids)
    sat_df = df[df["satellite_id"] == selected_sat].copy()

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Total Satellites:** {len(satellite_ids)}")
    st.sidebar.markdown(f"**Total Records:** {len(df):,}")
    st.sidebar.markdown(f"**Mode:** {mode}")

    page = st.sidebar.radio(
        "Navigation",
        ["Mission Overview", "Live Monitor", "Satellite Details", "Analytics",
         "Anomaly Detection", "AI Insights", "Reports"],
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Regenerate Data"):
        st.cache_resource.clear()
        st.session_state.data_ready = False
        st.rerun()

    # ── PAGE 1: Mission Overview ──
    if page == "Mission Overview":
        st.title("Mission Overview")
        st.markdown("### Fleet Health Status")

        col1, col2, col3, col4, col5 = st.columns(5)
        fleet_health = []
        excellent = good = warning = critical = 0
        total_score = 0

        with st.spinner("Computing fleet health..."):
            for sid in satellite_ids:
                sdf = df[df["satellite_id"] == sid]
                health = engines["health"].compute_health(sdf)
                score = health["overall_score"]
                total_score += score
                status = health["status"]
                fleet_health.append({"satellite_id": sid, "score": score, "status": status})
                if score >= 90:
                    excellent += 1
                elif score >= 70:
                    good += 1
                elif score >= 40:
                    warning += 1
                else:
                    critical += 1

        n = len(satellite_ids)
        avg_health = round(total_score / n, 1) if n > 0 else 0

        col1.metric("Total Satellites", n)
        col2.metric("Average Health", f"{avg_health}%")
        col3.metric("Excellent (90+)", excellent, delta=None, delta_color="off")
        col4.metric("Warning (40-70)", warning)
        col5.metric("Critical (<40)", critical, delta=None, delta_color="inverse")

        health_scores = {}
        for h in fleet_health:
            health_scores[h["satellite_id"]] = h["score"]

        st.plotly_chart(
            StatusCharts.progress_bars(health_scores, "Fleet Health Scores"),
            use_container_width=True,
        )

        st.markdown("### Satellite Health Distribution")
        dist_data = {"Excellent": excellent, "Good": good, "Warning": warning, "Critical": critical}
        st.plotly_chart(
            CircularCharts.donut_chart(dist_data, "Health Distribution", f"{avg_health}%"),
            use_container_width=True,
        )

        st.markdown("### Fleet Health Table")
        fleet_df = pd.DataFrame(fleet_health)
        fleet_df["color"] = fleet_df["score"].apply(lambda s: health_category(s)["color"])
        st.dataframe(fleet_df, use_container_width=True, hide_index=True)

    # ── PAGE: Live Monitor ──
    elif page == "Live Monitor":
        st.title("Live Telemetry Monitor")
        st.markdown("### Real-Time Satellite Telemetry Stream")

        import httpx

        col1, col2, col3 = st.columns(3)
        with col1:
            stream_sats = st.number_input("Satellites", 1, 50, 5, key="live_sats")
        with col2:
            stream_interval = st.number_input("Interval (ms)", 50, 5000, 200, 50, key="live_interval")
        with col3:
            stream_batch = st.number_input("Batch Size", 10, 500, 100, 10, key="live_batch")

        c1, c2 = st.columns([1, 3])
        with c1:
            start_btn = st.button("Start Live Stream", type="primary", use_container_width=True)
        with c2:
            stop_btn = st.button("Stop Stream", type="secondary", use_container_width=True)

        if start_btn:
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post(
                        "http://localhost:8000/api/stream/start",
                        params={
                            "satellites": stream_sats,
                            "interval_ms": stream_interval,
                            "batch_size": stream_batch,
                            "include_anomalies": True,
                        },
                    )
                    if resp.status_code == 200:
                        st.success(resp.json().get("message", "Stream started"))
                        st.session_state.stream_active = True
                    else:
                        st.error(f"Failed: {resp.text}")
            except Exception as e:
                st.warning(f"API not available: {e}. Running standalone mode.")

        if stop_btn:
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post("http://localhost:8000/api/stream/stop")
                    st.info("Stream stopped")
                    st.session_state.stream_active = False
            except Exception:
                st.info("Stream stopped")
                st.session_state.stream_active = False

        status_placeholder = st.empty()
        metrics_placeholder = st.empty()
        chart_placeholder = st.empty()

        if st.session_state.get("stream_active", False):
            st.markdown("### Live Telemetry Feed")

            cols = st.columns(4)
            cols[0].metric("Stream Status", "Active", delta="Live")
            cols[1].metric("Satellites", stream_sats)
            cols[2].metric("Interval", f"{stream_interval}ms")
            cols[3].metric("Batch Size", stream_batch)

            st.info("Live telemetry is being streamed and stored. Switch to other pages to analyze the incoming data.")

            st.markdown("---")
            st.markdown("### Latest Values")
            latest_placeholder = st.empty()

            with st.spinner("Waiting for live data..."):
                progress_bar = st.progress(0)
                for i in range(20):
                    try:
                        with httpx.Client(timeout=5) as client:
                            resp = client.get("http://localhost:8000/api/stream/status")
                            if resp.status_code == 200:
                                stats = resp.json()
                                cols = st.columns(5)
                                cols[0].metric("Buffer", stats.get("buffer_size", 0))
                                cols[1].metric("Ingested", stats.get("ingested_total", 0))
                                cols[2].metric("Flushed", stats.get("flushed_total", 0))
                                cols[3].metric("Dropped", stats.get("dropped_total", 0))
                                cols[4].metric("WS Clients", stats.get("ws_clients", 0))
                                progress_bar.progress(min(100, (i + 1) * 5))

                            resp2 = client.get("http://localhost:8000/api/stream/latest")
                            if resp2.status_code == 200:
                                latest_data = resp2.json()
                                satellites_data = latest_data.get("satellites", {})
                                if satellites_data:
                                    latest_records = []
                                    for sid, rec in list(satellites_data.items())[:5]:
                                        latest_records.append({
                                            "Satellite": sid,
                                            "Battery": rec.get("battery_pct", "N/A"),
                                            "Temp (°C)": rec.get("temperature_c", "N/A"),
                                            "Signal (dBm)": rec.get("signal_strength_dbm", "N/A"),
                                            "CPU (%)": rec.get("cpu_usage_pct", "N/A"),
                                            "Altitude (km)": rec.get("altitude_km", "N/A"),
                                        })
                                    latest_placeholder.dataframe(
                                        pd.DataFrame(latest_records),
                                        use_container_width=True, hide_index=True,
                                    )
                    except Exception:
                        pass
                    time.sleep(1)
                progress_bar.empty()

    # ── PAGE 2: Satellite Details ──
    elif page == "Satellite Details":
        st.title(f"Satellite Details: {selected_sat}")

        health = engines["health"].compute_health(sat_df)
        hc = health_category(health["overall_score"])

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### Health Score: {health['overall_score']:.1f}/100")
            st.markdown(f"**Status:** {health['status']}")
        with col2:
            st.markdown(f"**Records:** {len(sat_df)}")
            st.markdown(f"**Time Range:** {sat_df['timestamp'].min()} to {sat_df['timestamp'].max()}")
        with col3:
            st.plotly_chart(
                StatusCharts.health_gauge(health["overall_score"], selected_sat),
                use_container_width=True,
            )

        st.markdown("### Metric Scores")
        metric_data = {}
        for metric, info in health["metric_scores"].items():
            metric_data[metric] = info["score"]
        st.plotly_chart(
            StatusCharts.progress_bars(metric_data, "Component Health Scores"),
            use_container_width=True,
        )

        st.markdown("### Telemetry Time Series")
        tab1, tab2, tab3 = st.tabs(["Power & Thermal", "Communication & Computing", "Navigation"])

        with tab1:
            cols = st.columns(2)
            with cols[0]:
                st.plotly_chart(
                    TimeSeriesCharts.line_chart(sat_df, "battery_pct", "Battery Level", selected_sat),
                    use_container_width=True,
                )
            with cols[1]:
                st.plotly_chart(
                    TimeSeriesCharts.line_chart(sat_df, "temperature_c", "Temperature", selected_sat),
                    use_container_width=True,
                )
            st.plotly_chart(
                TimeSeriesCharts.multi_line_chart(
                    sat_df, ["solar_voltage_v", "current_a"], "Solar Power System", selected_sat
                ),
                use_container_width=True,
            )

        with tab2:
            cols = st.columns(2)
            with cols[0]:
                st.plotly_chart(
                    TimeSeriesCharts.line_chart(sat_df, "signal_strength_dbm", "Signal Strength", selected_sat),
                    use_container_width=True,
                )
            with cols[1]:
                st.plotly_chart(
                    TimeSeriesCharts.area_chart(sat_df, "cpu_usage_pct", "CPU Usage", selected_sat),
                    use_container_width=True,
                )
            st.plotly_chart(
                TimeSeriesCharts.line_chart(sat_df, "memory_usage_pct", "Memory Usage", selected_sat),
                use_container_width=True,
            )

        with tab3:
            st.plotly_chart(
                MissionCharts.ground_track(sat_df, selected_sat),
                use_container_width=True,
            )
            st.plotly_chart(
                TimeSeriesCharts.multi_line_chart(
                    sat_df, ["altitude_km", "velocity_kms"], "Orbit Parameters", selected_sat
                ),
                use_container_width=True,
            )

        st.markdown("### Raw Data")
        st.dataframe(sat_df.describe(), use_container_width=True)

    # ── PAGE 3: Analytics ──
    elif page == "Analytics":
        st.title(f"Analytics: {selected_sat}")

        stats = engines["analytics"].compute_statistics(sat_df)
        correlation = engines["analytics"].compute_correlation(sat_df)
        relationships = engines["analytics"].analyze_relationships(sat_df)
        ts_analysis = engines["analytics"].time_series_analysis(sat_df)
        distributions = engines["analytics"].distribution_analysis(sat_df)

        st.markdown("### Statistical Summary")
        stats_data = []
        for col_name, col_stats in stats.get("columns", {}).items():
            stats_data.append({
                "Metric": col_name,
                "Mean": f"{col_stats.mean:.2f}",
                "Std Dev": f"{col_stats.std_dev:.2f}",
                "Min": f"{col_stats.min:.2f}",
                "Max": f"{col_stats.max:.2f}",
                "Skewness": f"{col_stats.skewness:.2f}",
            })
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

        st.markdown("### Distributions")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                DistributionCharts.histogram(sat_df, "battery_pct", title="Battery Distribution"),
                use_container_width=True,
            )
            st.plotly_chart(
                DistributionCharts.histogram(sat_df, "signal_strength_dbm", title="Signal Distribution"),
                use_container_width=True,
            )
        with col2:
            st.plotly_chart(
                DistributionCharts.histogram(sat_df, "temperature_c", title="Temperature Distribution"),
                use_container_width=True,
            )
            st.plotly_chart(
                DistributionCharts.box_plot(
                    sat_df, ["battery_pct", "temperature_c", "cpu_usage_pct", "signal_strength_dbm"],
                    "Box Plot Comparison"
                ),
                use_container_width=True,
            )

        st.markdown("### Correlation Analysis")
        if not correlation.empty:
            st.plotly_chart(
                RelationshipCharts.correlation_heatmap(correlation),
                use_container_width=True,
            )

        st.markdown("### Key Relationships")
        rel_col1, rel_col2 = st.columns(2)
        for i, rel in enumerate(relationships[:6]):
            target_col = rel_col1 if i % 2 == 0 else rel_col2
            with target_col:
                st.metric(
                    rel["name"],
                    f"r = {rel['correlation']:.3f}",
                    delta=f"{rel['strength']} {rel['direction']}",
                )

        st.markdown("### Time Series Trends")
        trends = ts_analysis.get("trends", {})
        if trends:
            trend_data = []
            for col, info in trends.items():
                trend_data.append({
                    "Metric": col,
                    "Direction": info.get("direction", "stable"),
                    "Slope": f"{info.get('slope', 0):.6f}",
                    "Magnitude": f"{info.get('magnitude', 0):.6f}",
                })
            st.dataframe(pd.DataFrame(trend_data), use_container_width=True, hide_index=True)

        st.markdown("### Scatter Analysis")
        st.plotly_chart(
            RelationshipCharts.scatter_plot(sat_df, "battery_pct", "temperature_c",
                                            "Battery vs Temperature", selected_sat),
            use_container_width=True,
        )

    # ── PAGE 4: Anomaly Detection ──
    elif page == "Anomaly Detection":
        st.title(f"Anomaly Detection: {selected_sat}")

        analysis_df = engines["anomaly"].fit_detect(sat_df)
        anomalies = engines["anomaly"].classify_anomalies(analysis_df)
        anomaly_summary = engines["anomaly"].get_anomaly_summary(analysis_df, selected_sat)

        st.markdown("### Anomaly Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Anomalies", len(anomalies))
        col2.metric("ML Anomaly %", f"{anomaly_summary.get('ml_anomaly_pct', 0):.1f}%")
        col3.metric("Severity", anomaly_summary.get("severity", "None"))
        col4.metric("Records Analyzed", len(analysis_df))

        if anomalies:
            st.markdown("### Detected Anomalies")
            anomaly_df = pd.DataFrame(anomalies)
            if not anomaly_df.empty:
                anomaly_df["severity_color"] = anomaly_df["severity"].apply(
                    lambda s: "red" if s == "High" else "orange" if s == "Medium" else "green"
                )
                st.dataframe(
                    anomaly_df[["type", "timestamp", "metric", "value", "unit", "severity"]],
                    use_container_width=True, hide_index=True,
                )

            st.markdown("### Anomaly Visualization")
            st.plotly_chart(
                TimeSeriesCharts.line_chart(sat_df, "battery_pct", "Battery with Anomalies", selected_sat),
                use_container_width=True,
            )
            st.plotly_chart(
                TimeSeriesCharts.line_chart(sat_df, "temperature_c", "Temperature with Anomalies", selected_sat),
                use_container_width=True,
            )
        else:
            st.success("No anomalies detected for this satellite.")

        st.markdown("### Scatter: Battery vs Temperature (Anomaly Highlighted)")
        st.plotly_chart(
            RelationshipCharts.scatter_plot(sat_df, "battery_pct", "temperature_c",
                                            "Battery vs Temperature", selected_sat),
            use_container_width=True,
        )

    # ── PAGE 5: AI Insights ──
    elif page == "AI Insights":
        st.title(f"AI Insights: {selected_sat}")

        health = engines["health"].compute_health(sat_df)
        anomaly_summary = engines["anomaly"].get_anomaly_summary(
            engines["anomaly"].fit_detect(sat_df), selected_sat
        )
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

        insight_tab1, insight_tab2, insight_tab3 = st.tabs(["Engineer View", "Scientist View", "Student View"])

        with insight_tab1:
            explanation = engines["explainer"].explain(explanation_data, "engineer")
            st.code(explanation, language=None)

        with insight_tab2:
            explanation = engines["explainer"].explain(explanation_data, "scientist")
            st.code(explanation, language=None)

        with insight_tab3:
            explanation = engines["explainer"].explain(explanation_data, "student")
            st.markdown(explanation.replace("\n", "\n\n"))

            st.markdown("---")
            hc = health_category(health["overall_score"])
            st.markdown(f"### Overall Status: {hc['category']}")
            for metric, info in health["metric_scores"].items():
                st.progress(
                    info["score"] / 100,
                    text=f"{metric}: {info['score']:.0f}% - {info['status']}"
                )

    # ── PAGE 6: Reports ──
    elif page == "Reports":
        st.title("Reports & Export")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### CSV Export")
            csv_data = engines["reporter"].get_csv_bytes(sat_df)
            st.download_button(
                label="Download Telemetry CSV",
                data=csv_data,
                file_name=f"{selected_sat}_telemetry.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:
            st.markdown("### Excel Export")
            stats_df = pd.DataFrame(
                engines["analytics"].compute_statistics(sat_df).get("summary", {})
            ).T
            excel_bytes = engines["reporter"].get_excel_bytes({
                "Telemetry": sat_df,
                "Statistics": stats_df,
            })
            st.download_button(
                label="Download Excel Report",
                data=excel_bytes,
                file_name=f"{selected_sat}_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with col3:
            st.markdown("### JSON Report")
            health = engines["health"].compute_health(sat_df)
            stats = engines["analytics"].compute_statistics(sat_df)
            anomaly_summary = engines["anomaly"].get_anomaly_summary(sat_df, selected_sat)
            report = engines["reporter"].generate_telemetry_report_data(
                selected_sat, sat_df, stats, health, anomaly_summary, ""
            )
            json_bytes = engines["reporter"].get_json_bytes(report)
            st.download_button(
                label="Download JSON Report",
                data=json_bytes,
                file_name=f"{selected_sat}_report.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown("### Health Summary Report")
        health = engines["health"].compute_health(sat_df)
        st.markdown(f"**Satellite:** {selected_sat}")
        st.markdown(f"**Health Score:** {health['overall_score']}/100 — {health['status']}")

        report_data = []
        for metric, info in health["metric_scores"].items():
            report_data.append({
                "Metric": metric,
                "Value": info.get("value", "N/A"),
                "Score": info.get("score", "N/A"),
                "Status": info.get("status", "N/A"),
                "Unit": info.get("unit", ""),
            })
        st.dataframe(pd.DataFrame(report_data), use_container_width=True, hide_index=True)

        st.markdown("### Recommendations")
        for rec in health.get("recommendations", []):
            st.markdown(f"- {rec}")

        st.markdown("### Data Preview")
        st.dataframe(sat_df.head(50), use_container_width=True, hide_index=True)

else:
    st.title("ASTRA")
    st.markdown("### Advanced Satellite Telemetry & Real-time Analytics")
    st.markdown("---")
    st.markdown("""
    Welcome to ASTRA - the ISRO-grade satellite telemetry intelligence platform.

    **Getting Started:**
    1. Click **Quick Demo** in the sidebar to generate 10 satellites with anomalies
    2. Or use **Custom Generate** to create your own scenario
    3. Navigate through the dashboard to explore telemetry, analytics, and AI insights

    **Features:**
    - Realistic telemetry simulation with anomaly injection
    - Data validation and quality scoring
    - Comprehensive statistical analysis
    - ML-based anomaly detection (Isolation Forest)
    - AI-generated explanations (Engineer, Scientist, and Student modes)
    - 22+ professional visualization types
    - PDF, Excel, CSV, and JSON export
    """)
