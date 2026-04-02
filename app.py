"""Streamlit app: Natural Language to G-code Generator."""

from __future__ import annotations

import json
from typing import Any, Dict

import streamlit as st

from services.openai_client import OpenAIClientError, generate_gcode
from utils.gcode_parser import parse_gcode_toolpath
from utils.plotter import build_toolpath_figure
from utils.validators import analyze_gcode_safety, validate_required_fields


st.set_page_config(
    page_title="Natural Language to G-code Generator",
    page_icon="🖨️",
    layout="wide",
)


st.title("Natural Language to G-code Generator")
st.markdown(
    "Describe a constrained 3D printing request in plain English "
    "(e.g., calibration square, purge line, simple geometric path), "
    "and this app will generate draft G-code with assumptions and warnings."
)

st.warning(
    "Safety notice: Generated G-code must be manually reviewed before printing. "
    "For complex parts, use a slicer workflow.",
    icon="⚠️",
)


with st.sidebar:
    st.header("Printer Settings")

    firmware = st.selectbox("Printer firmware", ["Marlin", "Klipper", "RepRap", "Custom"])

    st.subheader("Build Volume (mm)")
    col_x, col_y, col_z = st.columns(3)
    bed_size_x = col_x.number_input("X", min_value=10.0, value=220.0, step=1.0)
    bed_size_y = col_y.number_input("Y", min_value=10.0, value=220.0, step=1.0)
    bed_size_z = col_z.number_input("Z", min_value=10.0, value=250.0, step=1.0)

    nozzle_diameter = st.number_input("Nozzle diameter (mm)", min_value=0.1, value=0.4, step=0.05)
    filament_type = st.selectbox("Filament type", ["PLA", "PETG", "ABS", "TPU", "Nylon", "Custom"])

    col_nt, col_bt = st.columns(2)
    nozzle_temp = col_nt.number_input("Nozzle temp (°C)", min_value=0.0, value=200.0, step=1.0)
    bed_temp = col_bt.number_input("Bed temp (°C)", min_value=0.0, value=60.0, step=1.0)

    layer_height = st.number_input("Layer height (mm)", min_value=0.05, value=0.2, step=0.01, format="%.2f")

    col_ps, col_ts = st.columns(2)
    print_speed = col_ps.number_input("Print speed (mm/s)", min_value=1.0, value=45.0, step=1.0)
    travel_speed = col_ts.number_input("Travel speed (mm/s)", min_value=1.0, value=120.0, step=1.0)

    extrusion_mode = st.selectbox("Extrusion mode", ["Absolute (M82)", "Relative (M83)"])
    include_start_gcode = st.checkbox("Include start G-code", value=True)
    include_end_gcode = st.checkbox("Include end G-code", value=True)


description = st.text_area(
    "Describe what you want to print",
    height=220,
    placeholder=(
        "Example: Generate a 20x20mm single-layer calibration square centered on bed, "
        "0.2mm layer height, two perimeters, no infill."
    ),
)

settings: Dict[str, Any] = {
    "firmware": firmware,
    "bed_size_x": bed_size_x,
    "bed_size_y": bed_size_y,
    "bed_size_z": bed_size_z,
    "nozzle_diameter": nozzle_diameter,
    "filament_type": filament_type,
    "nozzle_temp": nozzle_temp,
    "bed_temp": bed_temp,
    "layer_height": layer_height,
    "print_speed": print_speed,
    "travel_speed": travel_speed,
    "extrusion_mode": "M82" if "Absolute" in extrusion_mode else "M83",
    "include_start_gcode": include_start_gcode,
    "include_end_gcode": include_end_gcode,
}


if st.button("Generate G-code", type="primary", use_container_width=True):
    errors = validate_required_fields(description=description, settings=settings)
    if errors:
        for err in errors:
            st.error(err)
    else:
        with st.spinner("Generating G-code with OpenAI..."):
            try:
                result = generate_gcode(description=description, settings=settings)
            except OpenAIClientError as exc:
                st.error(str(exc))
            else:
                if not isinstance(result, dict):
                    st.error("Unexpected model response format. Please try again.")
                    st.stop()

                gcode_text = result.get("gcode")
                if not isinstance(gcode_text, str) or not gcode_text.strip():
                    st.error("Model response did not include valid G-code output.")
                    st.stop()

                safety_issues = analyze_gcode_safety(gcode_text, settings=settings)

                st.subheader("Toolpath Visualization")
                preview_warnings: list[str] = []
                try:
                    parsed = parse_gcode_toolpath(gcode_text)
                    preview_warnings = list(parsed.warnings)

                    if preview_warnings:
                        st.warning(
                            "Preview could not fully parse all G-code commands, showing partial path."
                        )

                    if parsed.segments:
                        fig = build_toolpath_figure(
                            segments=parsed.segments,
                            bed_x=float(settings["bed_size_x"]),
                            bed_y=float(settings["bed_size_y"]),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No preview available for this output.")
                except Exception:
                    preview_warnings.append(
                        "Preview could not fully parse all G-code commands, showing partial path."
                    )
                    st.warning("Preview could not fully parse all G-code commands, showing partial path.")
                    st.info("No preview available for this output.")

                st.caption(
                    "Preview is approximate and should not replace manual review or slicer validation."
                )

                st.subheader("Summary")
                st.write(result.get("summary", "No summary returned."))

                with st.expander("Assumptions", expanded=True):
                    assumptions = result.get("assumptions", [])
                    if assumptions:
                        for item in assumptions:
                            st.markdown(f"- {item}")
                    else:
                        st.write("No assumptions reported.")

                with st.expander("Warnings", expanded=True):
                    model_warnings = result.get("warnings", [])
                    combined_warnings = list(model_warnings) + safety_issues
                    if preview_warnings:
                        combined_warnings.append(
                            "Preview could not fully parse all G-code commands, showing partial path."
                        )

                    if combined_warnings:
                        for item in combined_warnings:
                            st.markdown(f"- {item}")
                    else:
                        st.write("No warnings reported.")

                st.subheader("Generated G-code")
                st.code(gcode_text, language="gcode")

                st.download_button(
                    "Download .gcode",
                    data=gcode_text,
                    file_name="generated_output.gcode",
                    mime="text/plain",
                )

                with st.expander("Raw JSON response", expanded=False):
                    st.code(json.dumps(result, indent=2), language="json")
