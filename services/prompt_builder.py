"""Prompt construction for Natural Language to G-code generation."""

from __future__ import annotations

import json
from typing import Any, Dict


SYSTEM_INSTRUCTIONS = """
You are a careful 3D-printer G-code assistant.
Generate safe, firmware-aware, constrained G-code from user requests.

Rules:
1) Output must be STRICT JSON only (no markdown, no prose outside JSON).
2) JSON keys exactly: summary, assumptions, warnings, gcode.
3) gcode must use semicolon comments where comments are helpful.
4) Prioritize safety: avoid unsafe temperatures, out-of-bounds motion, and undefined extrusion behavior.
5) If request is ambiguous/too complex for direct procedural pathing, return a safe response:
   - summary should ask for more detail or recommend slicer workflow,
   - assumptions should explain what is missing,
   - warnings should include safety cautions,
   - gcode should be minimal/safe and mostly comments (do not fabricate risky toolpaths).
6) Respect selected firmware conventions when possible.
7) Stay within bed dimensions.
8) Keep output practical for constrained tasks such as calibration square, purge line,
   simple vase-mode spiral, geometric paths, and custom motion patterns.
""".strip()


def build_user_prompt(description: str, settings: Dict[str, Any]) -> str:
    """Build the user-facing structured prompt payload."""
    payload = {
        "task": "Generate 3D-printer G-code from natural language request.",
        "user_request": description,
        "printer_settings": settings,
        "constraints": {
            "temperature_guidance": {
                "nozzle_c": "prefer 150-300C unless clearly justified",
                "bed_c": "prefer 0-120C unless clearly justified",
            },
            "bounds": "All XY and Z moves must stay within bed_size_x, bed_size_y, bed_size_z.",
            "homing": "If start_gcode is included, include a homing command where appropriate.",
            "comment_style": "Use semicolon comments in gcode output.",
            "extrusion_mode": "Respect absolute_vs_relative_extrusion setting.",
        },
        "required_output_json_schema": {
            "summary": "string",
            "assumptions": ["string", "..."],
            "warnings": ["string", "..."],
            "gcode": "string",
        },
    }

    return json.dumps(payload, indent=2)
