"""Validation helpers for inputs and generated G-code safety checks."""

from __future__ import annotations

import re
from typing import Any, Dict, List


COORD_PATTERN = re.compile(r"\b([XYZ])\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
TEMP_PATTERN = re.compile(r"\bM1(?:04|09)\s+S\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def validate_required_fields(description: str, settings: Dict[str, Any]) -> List[str]:
    """Validate required user input fields before sending request to model."""
    errors: List[str] = []

    if not description.strip():
        errors.append("Please describe what you want to print.")

    numeric_fields = [
        "bed_size_x",
        "bed_size_y",
        "bed_size_z",
        "nozzle_diameter",
        "nozzle_temp",
        "bed_temp",
        "layer_height",
        "print_speed",
        "travel_speed",
    ]

    for field in numeric_fields:
        value = settings.get(field)
        if value is None:
            errors.append(f"Missing required setting: {field}.")
            continue
        if value <= 0 and field not in {"bed_temp"}:
            errors.append(f"{field} must be greater than 0.")

    return errors


def analyze_gcode_safety(
    gcode: str,
    settings: Dict[str, Any],
) -> List[str]:
    """Run lightweight post-generation safety checks."""
    issues: List[str] = []

    bed_x = float(settings["bed_size_x"])
    bed_y = float(settings["bed_size_y"])
    bed_z = float(settings["bed_size_z"])

    for axis, value_str in COORD_PATTERN.findall(gcode):
        value = float(value_str)
        if axis.upper() == "X" and not (0 <= value <= bed_x):
            issues.append(f"Detected X coordinate out of bounds: {value} (0..{bed_x}).")
        elif axis.upper() == "Y" and not (0 <= value <= bed_y):
            issues.append(f"Detected Y coordinate out of bounds: {value} (0..{bed_y}).")
        elif axis.upper() == "Z" and not (0 <= value <= bed_z):
            issues.append(f"Detected Z coordinate out of bounds: {value} (0..{bed_z}).")

    nozzle_temps: List[float] = []
    bed_temps: List[float] = []
    for line in gcode.splitlines():
        line_upper = line.upper().strip()
        match = TEMP_PATTERN.search(line_upper)
        if not match:
            continue

        temp = float(match.group(1))
        if line_upper.startswith("M104") or line_upper.startswith("M109"):
            nozzle_temps.append(temp)
        else:
            bed_temps.append(temp)

    if any(t > 300 or t < 150 for t in nozzle_temps):
        issues.append("Detected nozzle target temperature outside typical safe range (150-300C).")

    if any(t > 120 or t < 0 for t in bed_temps):
        issues.append("Detected bed target temperature outside typical safe range (0-120C).")

    if settings.get("include_start_gcode"):
        has_homing = any(line.strip().upper().startswith("G28") for line in gcode.splitlines())
        if not has_homing:
            issues.append("Start G-code enabled, but no homing command (G28) was detected.")

    deduped = []
    seen = set()
    for issue in issues:
        if issue not in seen:
            deduped.append(issue)
            seen.add(issue)

    return deduped
