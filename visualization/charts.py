"""ASTRA Visualization Engine - 22+ Professional Chart Types"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional

from config.settings import VIZ_CONFIG
from utils.helpers import setup_logging

logger = setup_logging("astra.viz")

UNIT_LABELS = {
    "altitude_km": "Altitude (km)", "velocity_kms": "Velocity (km/s)",
    "battery_pct": "Battery (%)", "solar_voltage_v": "Solar Voltage (V)",
    "current_a": "Current (A)", "temperature_c": "Temperature (°C)",
    "cpu_usage_pct": "CPU Usage (%)", "memory_usage_pct": "Memory Usage (%)",
    "signal_strength_dbm": "Signal (dBm)", "radiation_level": "Radiation (rad)",
    "gyro_x": "Gyro X (°/s)", "gyro_y": "Gyro Y (°/s)", "gyro_z": "Gyro Z (°/s)",
    "accel_x": "Accel X (g)", "accel_y": "Accel Y (g)", "accel_z": "Accel Z (g)",
}


def _layout(fig, title, xlabel="", ylabel="", height=None, width=None):
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=18)),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_dark",
        height=height or VIZ_CONFIG["height"],
        width=width or VIZ_CONFIG["width"],
        hovermode="x unified",
        margin=dict(l=60, r=30, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _col_label(col: str) -> str:
    return UNIT_LABELS.get(col, col)


class TimeSeriesCharts:
    """Time series visualizations."""

    @staticmethod
    def line_chart(df: pd.DataFrame, col: str, title: str = None,
                   satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sat_df["timestamp"], y=sat_df[col],
            mode="lines", name=_col_label(col),
            line=dict(width=2, color=VIZ_CONFIG["color_palette"][0]),
        ))
        return _layout(fig, title or f"{_col_label(col)} Over Time",
                       "Time", _col_label(col))

    @staticmethod
    def multi_line_chart(df: pd.DataFrame, cols: List[str], title: str = None,
                         satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        for i, col in enumerate(cols):
            fig.add_trace(go.Scatter(
                x=sat_df["timestamp"], y=sat_df[col],
                mode="lines", name=_col_label(col),
                line=dict(width=2, color=VIZ_CONFIG["color_palette"][i % 10]),
            ))
        return _layout(fig, title or "Multi-Metric Time Series", "Time", "Value")

    @staticmethod
    def area_chart(df: pd.DataFrame, col: str, title: str = None,
                   satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sat_df["timestamp"], y=sat_df[col],
            mode="lines", fill="tozeroy", name=_col_label(col),
            line=dict(width=2, color=VIZ_CONFIG["color_palette"][0]),
            fillcolor=f"rgba(0,204,150,0.2)",
        ))
        return _layout(fig, title or f"{_col_label(col)} Area Chart",
                       "Time", _col_label(col))

    @staticmethod
    def step_chart(df: pd.DataFrame, col: str, title: str = None,
                   satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sat_df["timestamp"], y=sat_df[col],
            mode="lines", line_shape="hv", name=_col_label(col),
            line=dict(width=2, color=VIZ_CONFIG["color_palette"][1]),
        ))
        return _layout(fig, title or f"{_col_label(col)} Step Chart",
                       "Time", _col_label(col))


class ComparisonCharts:
    """Comparison and bar chart visualizations."""

    @staticmethod
    def bar_chart(values: Dict[str, float], title: str = "Bar Chart",
                  xlabel: str = "Category", ylabel: str = "Value") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(values.keys()), y=list(values.values()),
            marker_color=VIZ_CONFIG["color_palette"][:len(values)],
            text=[f"{v:.1f}" for v in values.values()],
            textposition="outside",
        ))
        return _layout(fig, title, xlabel, ylabel)

    @staticmethod
    def horizontal_bar(values: Dict[str, float], title: str = "Horizontal Bar",
                       xlabel: str = "Value", ylabel: str = "Category") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=list(values.keys()), x=list(values.values()),
            orientation="h",
            marker_color=VIZ_CONFIG["color_palette"][:len(values)],
            text=[f"{v:.1f}" for v in values.values()],
            textposition="outside",
        ))
        return _layout(fig, title, xlabel, ylabel)

    @staticmethod
    def grouped_bar(categories: List[str], groups: Dict[str, List[float]],
                    title: str = "Grouped Bar") -> go.Figure:
        fig = go.Figure()
        for i, (name, vals) in enumerate(groups.items()):
            fig.add_trace(go.Bar(
                x=categories, y=vals, name=name,
                marker_color=VIZ_CONFIG["color_palette"][i % 10],
            ))
        fig.update_layout(barmode="group")
        return _layout(fig, title, "Category", "Value")

    @staticmethod
    def stacked_bar(categories: List[str], groups: Dict[str, List[float]],
                    title: str = "Stacked Bar") -> go.Figure:
        fig = go.Figure()
        for i, (name, vals) in enumerate(groups.items()):
            fig.add_trace(go.Bar(
                x=categories, y=vals, name=name,
                marker_color=VIZ_CONFIG["color_palette"][i % 10],
            ))
        fig.update_layout(barmode="stack")
        return _layout(fig, title, "Category", "Value")

    @staticmethod
    def satellite_comparison(df_list: List[pd.DataFrame], sat_ids: List[str],
                             col: str, title: str = None) -> go.Figure:
        fig = go.Figure()
        for i, df in enumerate(df_list):
            val = df[col].mean()
            fig.add_trace(go.Bar(
                x=[sat_ids[i]], y=[val], name=sat_ids[i],
                marker_color=VIZ_CONFIG["color_palette"][i % 10],
                text=[f"{val:.1f}"], textposition="outside",
            ))
        return _layout(fig, title or f"Satellite Comparison - {_col_label(col)}",
                       "Satellite", _col_label(col))


class DistributionCharts:
    """Distribution analysis visualizations."""

    @staticmethod
    def histogram(df: pd.DataFrame, col: str, bins: int = 30,
                  title: str = None, satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=sat_df[col], nbinsx=bins, name=_col_label(col),
            marker_color=VIZ_CONFIG["color_palette"][0],
            marker_line=dict(color="white", width=0.5),
        ))
        return _layout(fig, title or f"Distribution of {_col_label(col)}",
                       _col_label(col), "Frequency")

    @staticmethod
    def box_plot(df: pd.DataFrame, cols: List[str],
                 title: str = "Box Plot", satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        for i, col in enumerate(cols):
            fig.add_trace(go.Box(
                y=sat_df[col], name=_col_label(col),
                marker_color=VIZ_CONFIG["color_palette"][i % 10],
            ))
        return _layout(fig, title, "Metric", "Value")

    @staticmethod
    def violin_plot(df: pd.DataFrame, cols: List[str],
                    title: str = "Violin Plot", satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        for i, col in enumerate(cols):
            fig.add_trace(go.Violin(
                y=sat_df[col], name=_col_label(col), box_visible=True,
                meanline_visible=True,
                marker_color=VIZ_CONFIG["color_palette"][i % 10],
            ))
        return _layout(fig, title, "Metric", "Value")


class RelationshipCharts:
    """Relationship and correlation visualizations."""

    @staticmethod
    def scatter_plot(df: pd.DataFrame, x_col: str, y_col: str,
                     title: str = None, satellite_id: str = None,
                     color_col: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        fig = go.Figure()
        marker = dict(
            size=6, opacity=0.6,
            color=sat_df[color_col] if color_col else VIZ_CONFIG["color_palette"][0],
            colorscale="Viridis" if color_col else None,
            showscale=bool(color_col),
            colorbar=dict(title=_col_label(color_col)) if color_col else None,
        )
        fig.add_trace(go.Scatter(
            x=sat_df[x_col], y=sat_df[y_col],
            mode="markers", marker=marker,
            name=f"{_col_label(x_col)} vs {_col_label(y_col)}",
        ))
        return _layout(fig, title or f"{_col_label(x_col)} vs {_col_label(y_col)}",
                       _col_label(x_col), _col_label(y_col))

    @staticmethod
    def bubble_chart(df: pd.DataFrame, x_col: str, y_col: str,
                     size_col: str, title: str = None,
                     satellite_id: str = None) -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id else df
        sizes = (sat_df[size_col] - sat_df[size_col].min()) / (
            sat_df[size_col].max() - sat_df[size_col].min()) * 30 + 5
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sat_df[x_col], y=sat_df[y_col],
            mode="markers", marker=dict(size=sizes, opacity=0.5, color=sizes, colorscale="Viridis"),
            name="",
        ))
        return _layout(fig, title or "Bubble Chart",
                       _col_label(x_col), _col_label(y_col))

    @staticmethod
    def correlation_heatmap(corr_matrix: pd.DataFrame,
                            title: str = "Correlation Heatmap") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Heatmap(
            z=corr_matrix.values,
            x=[UNIT_LABELS.get(c, c) for c in corr_matrix.columns],
            y=[UNIT_LABELS.get(c, c) for c in corr_matrix.index],
            colorscale="RdBu_r", zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont=dict(size=9),
        ))
        fig.update_layout(height=700, width=800)
        return _layout(fig, title, "", "")


class CircularCharts:
    """Circular chart visualizations."""

    @staticmethod
    def pie_chart(values: Dict[str, float], title: str = "Pie Chart") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=list(values.keys()), values=list(values.values()),
            marker=dict(colors=VIZ_CONFIG["color_palette"][:len(values)]),
            textinfo="label+percent", hole=0,
        ))
        return _layout(fig, title)

    @staticmethod
    def donut_chart(values: Dict[str, float], title: str = "Donut Chart",
                    center_text: str = "") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=list(values.keys()), values=list(values.values()),
            marker=dict(colors=VIZ_CONFIG["color_palette"][:len(values)]),
            textinfo="label+percent", hole=0.5,
        ))
        if center_text:
            fig.update_layout(annotations=[dict(
                text=center_text, x=0.5, y=0.5, font_size=20, showarrow=False
            )])
        return _layout(fig, title)

    @staticmethod
    def radar_chart(categories: List[str], values_list: List[Dict[str, float]],
                    title: str = "Radar Chart") -> go.Figure:
        fig = go.Figure()
        for i, entry in enumerate(values_list):
            vals = [entry.get(c, 0) for c in categories]
            vals.append(vals[0])
            cats = categories + [categories[0]]
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=cats, name=entry.get("name", f"Series {i+1}"),
                fill="toself",
                marker=dict(color=VIZ_CONFIG["color_palette"][i % 10]),
            ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        return _layout(fig, title)


class StatusCharts:
    """Status indicator visualizations."""

    @staticmethod
    def gauge_chart(value: float, title: str = "Gauge", max_val: float = 100,
                    thresholds: Dict[str, float] = None) -> go.Figure:
        if thresholds is None:
            thresholds = {"red": 40, "orange": 70, "green": 100}
        fig = go.Figure()
        steps = []
        colors_list = ["#EF553B", "#FFA15A", "#00CC96"]
        for i, (color_key, thresh) in enumerate(thresholds.items()):
            steps.append({"range": [0 if i == 0 else list(thresholds.values())[i-1], thresh],
                           "color": colors_list[i % len(colors_list)]})

        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            title={"text": title},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [0, max_val], "tickwidth": 1},
                "bar": {"color": "white"},
                "steps": steps,
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        ))
        fig.update_layout(height=350, width=400)
        return fig

    @staticmethod
    def health_gauge(score: float, satellite_id: str) -> go.Figure:
        from utils.helpers import health_category
        hc = health_category(score)
        return StatusCharts.gauge_chart(
            score, f"Health Score - {satellite_id}", 100,
            {"red": 40, "orange": 70, "green": 100},
        )

    @staticmethod
    def progress_bars(metrics: Dict[str, float], title: str = "Progress") -> go.Figure:
        names = list(metrics.keys())
        vals = list(metrics.values())
        fig = go.Figure()
        colors = []
        for v in vals:
            if v >= 80:
                colors.append("#00CC96")
            elif v >= 50:
                colors.append("#FFA15A")
            else:
                colors.append("#EF553B")
        fig.add_trace(go.Bar(
            y=names, x=vals, orientation="h",
            marker_color=colors,
            text=[f"{v:.0f}%" for v in vals],
            textposition="outside",
        ))
        fig.update_layout(xaxis_range=[0, 100])
        return _layout(fig, title, "Score (%)", "")


class MissionCharts:
    """Mission-specific visualizations."""

    @staticmethod
    def timeline_chart(events: List[Dict[str, Any]],
                       title: str = "Mission Timeline") -> go.Figure:
        fig = go.Figure()
        for i, event in enumerate(events):
            ts = event.get("timestamp")
            name = event.get("name", f"Event {i+1}")
            fig.add_trace(go.Scatter(
                x=[ts], y=[i], mode="markers+text",
                marker=dict(size=15, color=VIZ_CONFIG["color_palette"][i % 10]),
                text=[name], textposition="middle right",
                name=name,
            ))
        fig.update_layout(yaxis=dict(showticklabels=False))
        return _layout(fig, title, "Time", "")

    @staticmethod
    def orbit_3d(df: pd.DataFrame, satellite_id: str = None,
                 title: str = "3D Orbit Visualization") -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id and "satellite_id" in df.columns else df
        R = 6371.0

        lat_rad = np.radians(sat_df["latitude"])
        lon_rad = np.radians(sat_df["longitude"])
        alt = sat_df["altitude_km"] if "altitude_km" in sat_df.columns else 400

        r = R + alt.values if hasattr(alt, "values") else R + alt
        x = r * np.cos(lat_rad) * np.cos(lon_rad)
        y = r * np.cos(lat_rad) * np.sin(lon_rad)
        z = r * np.sin(lat_rad)

        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="lines",
            line=dict(width=3, color=VIZ_CONFIG["color_palette"][0]),
            name="Orbit Path",
        ))
        fig.add_trace(go.Scatter3d(
            x=[x.iloc[-1]], y=[y.iloc[-1]], z=[z.iloc[-1]],
            mode="markers", marker=dict(size=8, color=VIZ_CONFIG["color_palette"][1]),
            name="Current Position",
        ))

        u = np.linspace(0, 2*np.pi, 30)
        v = np.linspace(0, np.pi, 30)
        ex = R * np.outer(np.cos(u), np.sin(v))
        ey = R * np.outer(np.sin(u), np.sin(v))
        ez = R * np.outer(np.ones_like(u), np.cos(v))
        fig.add_trace(go.Surface(
            x=ex, y=ey, z=ez, colorscale="Blues",
            opacity=0.3, showscale=False, name="Earth",
        ))

        fig.update_layout(
            scene=dict(
                xaxis_title="X (km)", yaxis_title="Y (km)", zaxis_title="Z (km)",
                aspectmode="data",
            ),
            height=700, width=800,
        )
        return _layout(fig, title)

    @staticmethod
    def ground_track(df: pd.DataFrame, satellite_id: str = None,
                     title: str = "Ground Track") -> go.Figure:
        sat_df = df[df["satellite_id"] == satellite_id] if satellite_id and "satellite_id" in df.columns else df

        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lon=sat_df["longitude"], lat=sat_df["latitude"],
            mode="lines",
            line=dict(width=2, color=VIZ_CONFIG["color_palette"][0]),
            name="Ground Track",
        ))
        fig.add_trace(go.Scattergeo(
            lon=[sat_df["longitude"].iloc[-1]],
            lat=[sat_df["latitude"].iloc[-1]],
            mode="markers",
            marker=dict(size=10, color=VIZ_CONFIG["color_palette"][1], symbol="triangle-up"),
            name="Current Position",
        ))
        fig.update_geos(
            projection_type="orthographic",
            showcoastlines=True, coastlinecolor="white",
            showland=True, landcolor="rgb(50,50,50)",
            showocean=True, oceancolor="rgb(10,10,30)",
        )
        fig.update_layout(height=600, width=800)
        return _layout(fig, title)
