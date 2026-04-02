"""Plotly-based helpers for G-code toolpath visualization."""

from __future__ import annotations

from typing import Any, Dict, List

import plotly.graph_objects as go


def _build_trace_points(segments: List[Dict[str, Any]]) -> tuple[list[float], list[float], list[str]]:
    xs: list[float] = []
    ys: list[float] = []
    hovers: list[str] = []

    for index, seg in enumerate(segments, start=1):
        xs.extend([seg["x1"], seg["x2"], None])
        ys.extend([seg["y1"], seg["y2"], None])
        hover = (
            f"Segment #{index}<br>Line: {seg.get('line_number', 'n/a')}<br>"
            f"{seg.get('command', 'G?')} ({seg['x1']:.2f}, {seg['y1']:.2f}) → "
            f"({seg['x2']:.2f}, {seg['y2']:.2f})<br>Z: {seg.get('z', 0.0):.3f}"
        )
        hovers.extend([hover, hover, ""])

    return xs, ys, hovers


def build_toolpath_figure(segments: List[Dict[str, Any]], bed_x: float, bed_y: float) -> go.Figure:
    """Create a 2D top-down toolpath figure with bed outline and legend."""
    fig = go.Figure()

    bed_outline_x = [0, bed_x, bed_x, 0, 0]
    bed_outline_y = [0, 0, bed_y, bed_y, 0]
    fig.add_trace(
        go.Scatter(
            x=bed_outline_x,
            y=bed_outline_y,
            mode="lines",
            name="Bed Boundary",
            line={"color": "#2F2F2F", "width": 2, "dash": "dash"},
            hovertemplate="Bed boundary<extra></extra>",
        )
    )

    travel_segments = [seg for seg in segments if not seg.get("extruding", False)]
    extrusion_segments = [seg for seg in segments if seg.get("extruding", False)]

    if travel_segments:
        tx, ty, th = _build_trace_points(travel_segments)
        fig.add_trace(
            go.Scatter(
                x=tx,
                y=ty,
                mode="lines",
                name="Travel Moves",
                line={"color": "#1F77B4", "width": 2},
                hovertemplate="%{text}<extra></extra>",
                text=th,
            )
        )

    if extrusion_segments:
        ex, ey, eh = _build_trace_points(extrusion_segments)
        fig.add_trace(
            go.Scatter(
                x=ex,
                y=ey,
                mode="lines",
                name="Extrusion Moves",
                line={"color": "#D62728", "width": 3},
                hovertemplate="%{text}<extra></extra>",
                text=eh,
            )
        )

    fig.update_layout(
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        legend={"orientation": "h", "y": 1.05, "x": 0.0},
        hovermode="closest",
    )

    fig.update_xaxes(title_text="X (mm)", range=[0, max(bed_x, 1.0)], constrain="domain")
    fig.update_yaxes(title_text="Y (mm)", range=[0, max(bed_y, 1.0)], scaleanchor="x", scaleratio=1)

    return fig
