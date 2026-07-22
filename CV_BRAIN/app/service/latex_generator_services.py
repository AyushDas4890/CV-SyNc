"""
LaTeX Generator Service — Core orchestrator for CV generation.

Flow:
  1. Fetch concatenated .tex template from CV_BUILDER (or use provided latex_template)
  2. Build template-aware system prompt + user prompt
  3. Call LLM (Groq → OpenAI fallback → deterministic fallback)
  4. Validate output completeness
  5. Retry once with feedback if validation fails
  6. Sanitize + preamble-swap
  7. Return final .tex + engine info
"""

import httpx
from typing import List, Optional

from app.config.llmConfig import LLM
from app.config.serverConfig import Server_Credentials
from app.models import UserProfile, RepoDetail
from app.prompts.system_prompt import build_system_prompt
from app.prompts.user_prompt import build_user_prompt
from app.prompts.template_registry import get_template_metadata
from app.service.latex_sanitizer import (
    sanitize_generated_tex,
    replace_preamble_with_original,
    fallback_latex_filler,
)
from app.service.output_validator import validate_output

config = Server_Credentials()


# ── Template Fetching ────────────────────────────────────────────────────────

async def fetch_template_tex(template_id: str) -> str:
    """
    Fetch the concatenated .tex content from CV_BUILDER's
    GET /api/templates/:id/full endpoint.
    """
    cv_builder_url = config["CV_BUILDER_URL"].rstrip("/")
    url = f"{cv_builder_url}/api/templates/{template_id}/full"

    print(f"[LLM_BRAIN] Fetching template from: {url}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    if not data.get("success"):
        raise ValueError(f"CV_BUILDER returned error for template '{template_id}': {data}")

    tex = data.get("tex", "")
    if not tex:
        raise ValueError(f"CV_BUILDER returned empty tex for template '{template_id}'")

    print(f"[LLM_BRAIN] Fetched template '{template_id}': {len(tex)} chars")
    return tex


# ── LLM Calling ──────────────────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM. Returns raw response text or empty string on failure."""
    groq_api_key = config.get("GROQ_API_KEY")
    if not groq_api_key:
        print("[LLM_BRAIN] No GROQ_API_KEY configured, skipping Groq.")
        return ""

    try:
        llm_instance = LLM(
            modelName=config["GROQ_MODEL"],
            api_key=groq_api_key,
            temperature=float(config.get("GROQ_TEMPERATURE", "0.1")),
            maxTokens=int(config.get("GROQ_MAX_TOKENS", "8192")),
        )
        llm = llm_instance.get_groq_client()

        print(f"[LLM_BRAIN] Calling Groq ({config['GROQ_MODEL']})...")
        res = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return res.content or ""
    except Exception as e:
        print(f"[LLM_BRAIN] Groq call failed: {e}")
        return ""


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI LLM. Returns raw response text or empty string on failure."""
    openai_api_key = config.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("[LLM_BRAIN] No OPENAI_API_KEY configured, skipping OpenAI.")
        return ""

    try:
        # NOTE: was importing from langchain_community.chat_models, which is both the
        # deprecated location and a package not listed in pyproject.toml — this call
        # would have raised ImportError the first time it actually ran. Fixed to the
        # current package (added to pyproject.toml as a new dependency).
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=openai_api_key,
            temperature=0.2,
            max_tokens=int(config.get("GROQ_MAX_TOKENS", "8192")),
        )
        print("[LLM_BRAIN] Calling OpenAI (gpt-4o-mini)...")
        res = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return res.content or ""
    except Exception as e:
        print(f"[LLM_BRAIN] OpenAI call failed: {e}")
        return ""


def _has_valid_tex(text: str) -> bool:
    """Check if the text contains a valid LaTeX document structure."""
    return bool(text and r"\documentclass" in text)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call LLM with OpenAI -> Groq fallback chain.
    (Was Groq-first; switched per Ayush's request to run on OpenAI for now.
    Groq stays as a fallback in case OPENAI_API_KEY is unset/rate-limited.)
    Returns the raw LLM response text.
    """
    # Try OpenAI first
    result = _call_openai(system_prompt, user_prompt)
    if _has_valid_tex(result):
        return result

    # Fallback to Groq
    result = _call_groq(system_prompt, user_prompt)
    if _has_valid_tex(result):
        return result

    return ""


def strip_latex_comments(tex: str) -> str:
    """Remove comments from LaTeX code to save tokens."""
    import re
    lines = tex.split('\n')
    cleaned_lines = []
    for line in lines:
        # Regex to match '%' not preceded by a backslash '\'
        cleaned = re.sub(r'(?<!\\)%.*$', '', line).rstrip()
        cleaned_lines.append(cleaned)
    return '\n'.join(cleaned_lines)


# ── Core Orchestrator ─────────────────────────────────────────────────────────

async def generate_cv(
    user_profile: UserProfile,
    selected_repos: List[RepoDetail],
    template_id: str = "Jake_s_Resume__3_",
    target_role: str = "",
    target_pages: int = 1,
    latex_template: Optional[str] = None,
) -> dict:
    """
    Main CV generation pipeline:
    1. Fetch template (or use provided one)
    2. Build prompts
    3. Call LLM
    4. Validate → retry if needed
    5. Sanitize + preamble-swap
    6. Return result
    """

    # ── Step 1: Get the template tex ──────────────────────────────────────
    if latex_template and _has_valid_tex(latex_template):
        template_tex = latex_template
        print(f"[LLM_BRAIN] Using provided latex_template ({len(template_tex)} chars)")
    else:
        template_tex = await fetch_template_tex(template_id)

    # ── Step 2: Get template metadata for engine info ─────────────────────
    template_meta = get_template_metadata(template_id)
    engine = template_meta["engine"] if template_meta else "pdflatex"

    # ── Step 3: Build prompts ─────────────────────────────────────────────
    clean_template_tex = strip_latex_comments(template_tex)
    user_prompt, has_experience, has_education = build_user_prompt(
        user_profile, selected_repos, clean_template_tex
    )
    system_prompt = build_system_prompt(
        template_id=template_id,
        has_experience=has_experience,
        has_education=has_education,
        target_pages=target_pages,
    )

    print(
        f"[LLM_BRAIN] Template: {template_id}, Engine: {engine}, "
        f"Repos: {len(selected_repos)}, Has exp: {has_experience}, "
        f"Has edu: {has_education}, Template size: {len(template_tex)} chars"
    )

    # ── Step 4: Call LLM (attempt 1) ──────────────────────────────────────
    edited_tex = call_llm(system_prompt, user_prompt)

    # ── Step 5: Validate output ───────────────────────────────────────────
    validation_passed = True
    validation_failures = []

    if _has_valid_tex(edited_tex):
        validation = validate_output(
            edited_tex, user_profile, has_experience, has_education
        )

        # ── Step 5b: Retry once if validation failed ──────────────────────
        if not validation.passed:
            print(
                f"[LLM_BRAIN] Attempt 1 validation failed: {validation.failures}. "
                f"Retrying with feedback..."
            )
            retry_prompt = (
                f"Your previous output was INCOMPLETE. The following checks failed:\n"
                f"  {', '.join(validation.failures)}\n\n"
                f"You MUST fix ALL of these issues. Return the COMPLETE LaTeX document "
                f"from \\documentclass to \\end{{document}} with ALL sections filled. "
                f"Make sure the resume fills a full page with substantial content.\n\n"
                f"{user_prompt}"
            )
            retry_tex = call_llm(system_prompt, retry_prompt)
            if _has_valid_tex(retry_tex):
                retry_validation = validate_output(
                    retry_tex, user_profile, has_experience, has_education
                )
                if retry_validation.passed:
                    edited_tex = retry_tex
                    validation_passed = True
                else:
                    validation_passed = False
                    validation_failures = retry_validation.failures
                    # Keep retry if it's better
                    if len(retry_validation.failures) < len(validation.failures):
                        edited_tex = retry_tex
            else:
                validation_passed = False
                validation_failures = validation.failures
        else:
            validation_passed = True
    else:
        validation_passed = False
        validation_failures = ["no_valid_latex_structure_received_from_llm"]

    # Raise error if validation failed so fallback does not silently return placeholders
    if not validation_passed:
        raise ValueError(
            f"Resume validation failed: {', '.join(validation_failures)}. "
            "Please ensure your LLM API keys are valid and not rate-limited (TPD/TPM limits)."
        )

    # ── Step 7: Sanitize ──────────────────────────────────────────────────
    edited_tex = sanitize_generated_tex(edited_tex)

    # ── Step 8: Preamble swap (use original template preamble) ────────────
    edited_tex = replace_preamble_with_original(edited_tex, template_tex)

    # ── Logging ───────────────────────────────────────────────────────────
    lines = edited_tex.split('\n')
    print(f"[LLM_BRAIN] Final TeX: {len(lines)} lines, {len(edited_tex)} chars")
    print(f"[LLM_BRAIN] First 5 lines:")
    for i, l in enumerate(lines[:5], start=1):
        print(f"  {i}: {l}")
    has_docclass = r'\documentclass' in edited_tex
    has_begindoc = r'\begin{document}' in edited_tex
    has_enddoc = r'\end{document}' in edited_tex
    print(
        f"[LLM_BRAIN] Has \\documentclass: {has_docclass}, "
        f"Has \\begin{{document}}: {has_begindoc}, "
        f"Has \\end{{document}}: {has_enddoc}"
    )

    return {
        "ok": True,
        "tex": edited_tex,
        "engine": engine,
        "template_id": template_id,
        "summary": "Resume generated successfully with template-aware prompting and completeness validation.",
    }
