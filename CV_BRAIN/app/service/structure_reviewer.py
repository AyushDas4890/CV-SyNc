"""
Structure reviewer — a second LLM pass that audits the generated .tex against
the template it was meant to fill.

The deterministic validator (output_validator.py) checks that required things
are PRESENT. This checks that what is present is STRUCTURALLY CORRECT for the
chosen template — invented macros, damaged preamble, unbalanced environments —
which is not practical to express as regex rules across eight different
templates.

Advisory by design: a review that fails to parse must never sink a generation
that is otherwise fine.
"""

import json
import re
from typing import Optional

from app.prompts.review_prompts import build_structure_review_prompt

FATAL_SEVERITIES = {"fatal", "major"}


def _extract_json(raw: str) -> Optional[dict]:
    """
    Pull a JSON object out of an LLM response.

    Models wrap JSON in markdown fences or prose often enough that requiring
    clean output is not realistic, so strip fences first, then fall back to
    grabbing the outermost braces.
    """
    if not raw:
        return None

    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def parse_review(raw: str) -> dict:
    """
    Normalise an LLM review response into a predictable shape.

    Always returns {structure_ok, issues, summary, parsed}. `parsed` is False
    when the model's answer could not be read — the caller treats that as
    "no opinion", not as a failure.
    """
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return {
            "structure_ok": True,
            "issues": [],
            "summary": "structure review response could not be parsed; skipped",
            "parsed": False,
        }

    issues = data.get("issues") or []
    if not isinstance(issues, list):
        issues = []
    issues = [i for i in issues if isinstance(i, dict)]

    blocking = [i for i in issues if str(i.get("severity", "")).lower() in FATAL_SEVERITIES]

    # Trust the issue list over the model's own boolean — models sometimes say
    # structure_ok:true while listing fatal problems.
    structure_ok = bool(data.get("structure_ok", True)) and not blocking

    return {
        "structure_ok": structure_ok,
        "issues": issues,
        "blocking_issues": blocking,
        "summary": str(data.get("summary", ""))[:500],
        "parsed": True,
    }


def build_review_call(template_id: str, template_tex: str, generated_tex: str) -> tuple:
    """Return (system_prompt, user_prompt) for the structure audit."""
    return build_structure_review_prompt(template_id, template_tex, generated_tex)
