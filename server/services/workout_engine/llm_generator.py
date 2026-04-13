"""LLM client for structured workout generation using Groq chat completions."""

import json
import os
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv


DEFAULT_GROQ_MODEL = "llama3-70b-8192"
FALLBACK_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


# Ensure server/.env is loaded regardless of current working directory.
SERVER_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVER_ROOT / ".env")


class WorkoutLLMError(RuntimeError):
    """Raised when LLM output is missing or invalid."""


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise WorkoutLLMError("LLM did not return parseable JSON")
        return json.loads(raw[start : end + 1])


def _build_prompt(constraints: Dict[str, Any]) -> str:
    return (
        "You are a certified strength and conditioning coach working inside a Hybrid AI Fitness Planning System.\n"
        "Return ONLY valid JSON. No markdown. No prose.\n"
        "\n"
        "CRITICAL RULES:\n"
        "- Do NOT change workout split\n"
        "- Do NOT change total weekly volume per muscle\n"
        "- Do NOT add extra training days\n"
        "- Do NOT violate rest days\n"
        "- Do NOT include unsafe or injury-conflicting exercises\n"
        "- Use only exercises from allowed_exercises_by_muscle\n"
        "\n"
        "Use these backend constraints exactly:\n"
        f"{json.dumps(constraints, ensure_ascii=True)}\n"
        "\n"
        "Output schema strictly:\n"
        "{\"weekly_plan\":{\"day_1\":{\"type\":\"push/pull/legs/upper/lower/full_body/rest\",\"exercises\":[{\"exercise\":\"...\",\"muscle\":\"...\",\"sets\":1,\"reps\":\"8-12\",\"rest\":\"60 sec\"}]}}}\n"
        "\n"
        "Rules:\n"
        "- Include day_1 through day_7\n"
        "- For rest days, exercises must be []\n"
        "- For training days, exercise count must be between min_exercises_per_day and max_exercises_per_day\n"
        "- Keep compound movements before isolation movements\n"
        "- reps must match the exact required_rep_range\n"
        "- Weekly sets per muscle must equal weekly_volume_per_muscle\n"
    )


def generate_workout_with_llm(constraints: Dict[str, Any]) -> Dict[str, Any]:
    """Generate workout JSON using Groq and return parsed object."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise WorkoutLLMError("GROQ_API_KEY is not configured")

    # Try requested model first, then an automatic fallback if Groq decommissions it.
    models_to_try = [DEFAULT_GROQ_MODEL, os.getenv("GROQ_FALLBACK_MODEL", FALLBACK_GROQ_MODEL).strip() or FALLBACK_GROQ_MODEL]
    prompt = _build_prompt(constraints)
    last_error = ""

    for model in models_to_try:
        payload = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": "You output only strict JSON."},
                {"role": "user", "content": prompt},
            ],
        }

        try:
            response = requests.post(
                GROQ_BASE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )
        except requests.RequestException as exc:
            raise WorkoutLLMError(f"Groq network error: {exc}")

        response_data: Dict[str, Any] = {}
        try:
            response_data = response.json()
        except ValueError:
            if response.status_code >= 400:
                raise WorkoutLLMError(f"Groq API error {response.status_code}: non-JSON body")

        if response.status_code >= 400:
            error_message = str(response_data.get("error", {}).get("message", "")).lower()
            error_code = str(response_data.get("error", {}).get("code", "")).lower()
            last_error = f"Groq API error {response.status_code}: {response_data.get('error', {}).get('message', 'unknown error')}"
            if response.status_code == 400 and ("model_decommissioned" in error_code or "decommissioned" in error_message):
                continue
            raise WorkoutLLMError(last_error)

        choices = response_data.get("choices", [])
        if not choices:
            last_error = "LLM returned no choices"
            continue

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            last_error = "LLM returned empty response"
            continue

        parsed = _extract_json_object(content)
        if not isinstance(parsed, dict):
            last_error = "LLM response is not a JSON object"
            continue
        return parsed

    raise WorkoutLLMError(last_error or "LLM generation failed for all configured models")
