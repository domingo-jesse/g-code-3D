"""Utilities for parsing G-code into plottable 2D path segments."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List


MOVE_COMMANDS = {"G0", "G00", "G1", "G01"}
PARAM_PATTERN = re.compile(r"([A-Za-z])\s*(-?\d+(?:\.\d+)?)")


@dataclass
class ParseResult:
    """Container for parser output and metadata."""

    segments: List[Dict[str, Any]]
    warnings: List[str]
    partial: bool = False


def _strip_inline_comment(line: str) -> str:
    """Remove ';' and parenthesized comments from a line."""
    no_semicolon = line.split(";", 1)[0]
    return re.sub(r"\([^)]*\)", "", no_semicolon).strip()


def _to_float(token: str) -> float | None:
    try:
        return float(token)
    except ValueError:
        return None


def parse_gcode_toolpath(gcode: str) -> ParseResult:
    """Parse basic G0/G1 XY segments with extrusion detection.

    Supports common absolute/relative movement (G90/G91) and extrusion mode (M82/M83).
    """
    segments: List[Dict[str, Any]] = []
    warnings: List[str] = []
    partial = False

    x = 0.0
    y = 0.0
    z = 0.0
    e = 0.0

    absolute_positioning = True  # G90 / G91
    absolute_extrusion = True  # M82 / M83

    lines = gcode.splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = _strip_inline_comment(raw_line)
        if not line:
            continue

        upper = line.upper()
        if upper.startswith("G90"):
            absolute_positioning = True
            continue
        if upper.startswith("G91"):
            absolute_positioning = False
            continue
        if upper.startswith("M82"):
            absolute_extrusion = True
            continue
        if upper.startswith("M83"):
            absolute_extrusion = False
            continue
        if upper.startswith("G92"):
            params = {k.upper(): v for k, v in PARAM_PATTERN.findall(line)}
            if "X" in params and (val := _to_float(params["X"])) is not None:
                x = val
            if "Y" in params and (val := _to_float(params["Y"])) is not None:
                y = val
            if "Z" in params and (val := _to_float(params["Z"])) is not None:
                z = val
            if "E" in params and (val := _to_float(params["E"])) is not None:
                e = val
            continue

        command = line.split()[0].upper()
        if command not in MOVE_COMMANDS:
            continue

        params = {k.upper(): v for k, v in PARAM_PATTERN.findall(line)}

        x2, y2, z2, e2 = x, y, z, e

        if "X" in params:
            x_val = _to_float(params["X"])
            if x_val is None:
                warnings.append(f"Line {line_number}: invalid X value; skipped move.")
                partial = True
                continue
            x2 = x_val if absolute_positioning else x + x_val

        if "Y" in params:
            y_val = _to_float(params["Y"])
            if y_val is None:
                warnings.append(f"Line {line_number}: invalid Y value; skipped move.")
                partial = True
                continue
            y2 = y_val if absolute_positioning else y + y_val

        if "Z" in params:
            z_val = _to_float(params["Z"])
            if z_val is None:
                warnings.append(f"Line {line_number}: invalid Z value; keeping prior Z.")
                partial = True
            else:
                z2 = z_val if absolute_positioning else z + z_val

        if "E" in params:
            e_val = _to_float(params["E"])
            if e_val is None:
                warnings.append(f"Line {line_number}: invalid E value; unable to detect extrusion.")
                partial = True
            else:
                e2 = e_val if absolute_extrusion else e + e_val

        extruding = False
        if "E" in params and e2 > e:
            extruding = True

        if (x2 != x or y2 != y) and all(v is not None for v in [x, y, x2, y2]):
            segments.append(
                {
                    "x1": float(x),
                    "y1": float(y),
                    "x2": float(x2),
                    "y2": float(y2),
                    "z": float(z2),
                    "extruding": extruding,
                    "command": command,
                    "line_number": line_number,
                    "feedrate": _to_float(params["F"]) if "F" in params else None,
                }
            )

        x, y, z, e = x2, y2, z2, e2

    # Deduplicate warnings while preserving order.
    deduped_warnings: List[str] = []
    seen: set[str] = set()
    for warning in warnings:
        if warning not in seen:
            deduped_warnings.append(warning)
            seen.add(warning)

    return ParseResult(segments=segments, warnings=deduped_warnings, partial=partial)
