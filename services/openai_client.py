"""OpenAI Responses API client for G-code generation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

from services.prompt_builder import SYSTEM_INSTRUCTIONS, build_user_prompt


MODEL_NAME = "gpt-4.1-mini"


class OpenAIClientError(Exception):
    """Raised when generation via OpenAI fails."""


def _extract_text_output(response: Any) -> str:
    """Extract text content from a Responses API response robustly."""
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def generate_gcode(description: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Generate structured G-code output using the OpenAI Responses API."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIClientError(
            "OPENAI_API_KEY is not set. Add it to your environment or .env file."
        )

    client = OpenAI(api_key=api_key)
    user_prompt = build_user_prompt(description=description, settings=settings)

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        raise OpenAIClientError(f"OpenAI API request failed: {exc}") from exc

    raw_text = _extract_text_output(response)
    if not raw_text:
        raise OpenAIClientError("Model returned an empty response.")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError(
            "Model output was not valid JSON. Please try again with a more specific request."
        ) from exc

    required_keys = {"summary", "assumptions", "warnings", "gcode"}
    if not required_keys.issubset(parsed.keys()):
        raise OpenAIClientError(
            "Model JSON response missing required keys: summary, assumptions, warnings, gcode."
        )

    return parsed
