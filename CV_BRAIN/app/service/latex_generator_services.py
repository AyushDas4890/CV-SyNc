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

import anyio.to_thread
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
from app.service.compile_client import compile_tex
from app.service.page_metrics import measure_pdf, classify, expected_pages
from app.service.structure_reviewer import build_review_call, parse_review
from app.prompts.review_prompts import (
    build_structure_repair_prompt,
    build_page_fit_prompt,
    build_macro_arity_repair_prompt,
)
from app.service.macro_validator import (
    extract_macro_arity,
    check_macro_calls,
    describe_macro_signatures,
    format_problems,
    fix_duplicate_label_colons,
)

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
    import traceback
    openai_api_key = config.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("[LLM_BRAIN] No OPENAI_API_KEY configured, skipping OpenAI.")
        return ""

    # Safety cap: gpt-4o-mini has a 128k token context. Each char ≈ 0.25 tokens.
    # Cap total prompt at 100k chars (~25k tokens input) to leave room for output.
    MAX_PROMPT_CHARS = 100_000
    total_chars = len(system_prompt) + len(user_prompt)
    print(f"[LLM_BRAIN] Prompt size: {total_chars} chars (~{total_chars // 4} tokens est)")
    if total_chars > MAX_PROMPT_CHARS:
        print(f"[LLM_BRAIN] WARNING: Prompt exceeds {MAX_PROMPT_CHARS} chars, truncating user_prompt.")
        # Keep at least 10k chars of user prompt. The old `user_prompt[:-overflow]`
        # silently produced an EMPTY prompt whenever the overflow was >= the user
        # prompt length (large system prompt / huge template), which made the LLM
        # return garbage for no visible reason.
        keep = max(10_000, MAX_PROMPT_CHARS - len(system_prompt))
        user_prompt = user_prompt[:keep]
        print(f"[LLM_BRAIN] user_prompt truncated to {len(user_prompt)} chars.")

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
        output = res.content or ""
        print(f"[LLM_BRAIN] OpenAI response: {len(output)} chars, has_documentclass={chr(92) + 'documentclass' in output}")
        return output
    except Exception as e:
        print(f"[LLM_BRAIN] OpenAI call FAILED — {type(e).__name__}: {e}")
        traceback.print_exc()
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
    print("[LLM_BRAIN] Trying OpenAI...")
    result = _call_openai(system_prompt, user_prompt)
    if _has_valid_tex(result):
        print("[LLM_BRAIN] OpenAI returned valid LaTeX.")
        return result
    else:
        print(f"[LLM_BRAIN] OpenAI did NOT return valid LaTeX (len={len(result)}). Trying Groq fallback...")
        if result:
            print(f"[LLM_BRAIN] OpenAI raw output (first 200): {result[:200]!r}")

    # Fallback to Groq
    result = _call_groq(system_prompt, user_prompt)
    if _has_valid_tex(result):
        print("[LLM_BRAIN] Groq returned valid LaTeX.")
        return result
    else:
        print(f"[LLM_BRAIN] Groq also did NOT return valid LaTeX (len={len(result)}).")
        if result:
            print(f"[LLM_BRAIN] Groq raw output (first 200): {result[:200]!r}")

    return ""


async def call_llm_async(system_prompt: str, user_prompt: str) -> str:
    """
    Await `call_llm` on a worker thread.

    LangChain's `.invoke()` is blocking. Calling it directly from the async
    request handler pins the event loop for the entire LLM round-trip (tens of
    seconds), so every other request — including /health — stalls behind a
    single CV generation. Off-loading to a thread keeps the server responsive.
    """
    return await anyio.to_thread.run_sync(call_llm, system_prompt, user_prompt)


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


# ── Refinement passes ────────────────────────────────────────────────────────

def _finalize(tex: str, template_tex: str) -> str:
    """Sanitize + restore the original preamble. What actually gets compiled."""
    return replace_preamble_with_original(sanitize_generated_tex(tex), template_tex)


async def enforce_macro_arity(
    tex: str,
    template_tex: str,
    template_id: str,
    max_attempts: int = 2,
) -> tuple:
    """
    Deterministically check every macro call against the arity declared in the
    template source, and repair any call that supplies too few arguments.

    This runs BEFORE the compile because a wrong-arity call is always fatal and
    the resulting TeX error ("Missing number, treated as zero") points at the
    symptom rather than the cause. Catching it here is far cheaper and clearer
    than letting the compile fail.

    Returns (tex, remaining_problems).
    """
    arity = extract_macro_arity(template_tex)
    if not arity:
        return tex, []

    # Two-argument bullet macros insert ": " themselves, so a label written as
    # "Tech Stack:" renders "Tech Stack:: ...". Seen in real output; fixed
    # deterministically because prompting alone doesn't reliably prevent it.
    tex, colon_fixes = fix_duplicate_label_colons(tex, arity)
    if colon_fixes:
        print(f"[LLM_BRAIN] Macro labels: removed {colon_fixes} duplicated colon(s)")

    problems = check_macro_calls(tex, arity)
    if not problems:
        return tex, []

    signatures = describe_macro_signatures(arity)

    for attempt in range(1, max_attempts + 1):
        print(
            f"[LLM_BRAIN] Macro arity: {len(problems)} bad call(s) "
            f"(attempt {attempt}/{max_attempts})"
        )
        for p in problems[:5]:
            print(
                f"[LLM_BRAIN]   line {p['line']}: \\{p['macro']} "
                f"needs {p['expected']}, got {p['found']}"
            )

        repair_prompt = build_macro_arity_repair_prompt(
            template_tex, tex, format_problems(problems), signatures
        )
        system_prompt = build_system_prompt(
            template_id=template_id,
            has_experience=True,
            has_education=True,
            target_pages="auto",
            macro_signatures=signatures,
        )
        repaired = await call_llm_async(system_prompt, repair_prompt)
        if not _has_valid_tex(repaired):
            print("[LLM_BRAIN] Macro arity repair returned no valid LaTeX — stopping")
            break

        candidate = _finalize(repaired, template_tex)
        remaining = check_macro_calls(candidate, arity)
        if len(remaining) < len(problems):
            tex, problems = candidate, remaining
        if not problems:
            print("[LLM_BRAIN] Macro arity: all calls fixed")
            return tex, []

    return tex, problems


async def run_structure_review(
    template_id: str,
    template_tex: str,
    generated_tex: str,
) -> dict:
    """
    Ask the LLM whether the generated document respects the template.

    Advisory: any failure here returns "no opinion" rather than raising, so a
    flaky review can never sink an otherwise good generation.
    """
    system_prompt, user_prompt = build_review_call(template_id, template_tex, generated_tex)
    try:
        raw = await call_llm_async(system_prompt, user_prompt)
    except Exception as exc:
        print(f"[LLM_BRAIN] Structure review call failed: {type(exc).__name__}: {exc}")
        return {
            "structure_ok": True,
            "issues": [],
            "summary": "structure review unavailable",
            "parsed": False,
        }

    review = parse_review(raw)
    if review["parsed"]:
        print(
            f"[LLM_BRAIN] Structure review: ok={review['structure_ok']} "
            f"issues={len(review['issues'])} — {review['summary']}"
        )
        for issue in review["issues"]:
            print(
                f"[LLM_BRAIN]   [{issue.get('severity')}] "
                f"{issue.get('location')}: {issue.get('problem')}"
            )
    else:
        print("[LLM_BRAIN] Structure review response unparseable — skipping")
    return review


async def apply_structure_repair(
    template_id: str,
    template_tex: str,
    generated_tex: str,
    issues: list,
) -> Optional[str]:
    """
    Run one repair pass for the structural issues found.

    Returns the repaired tex, or None if the repair produced nothing usable —
    in which case the caller keeps the original, since a broken repair is
    worse than a document with known cosmetic issues.
    """
    system_prompt = build_system_prompt(
        template_id=template_id,
        has_experience=True,
        has_education=True,
        target_pages="auto",
    )
    repair_prompt = build_structure_repair_prompt(
        template_id, template_tex, generated_tex, issues
    )
    repaired = await call_llm_async(system_prompt, repair_prompt)
    if not _has_valid_tex(repaired):
        print("[LLM_BRAIN] Structure repair returned no valid LaTeX — keeping original")
        return None
    return _finalize(repaired, template_tex)


async def fit_to_page_target(
    tex: str,
    template_tex: str,
    template_id: str,
    engine: str,
    target_pages,
) -> dict:
    """
    Compile → measure → expand/condense until the document lands on an
    allowed page band (1, 1.5 or 2 pages).

    target_pages of "auto" snaps to whichever band the first compile lands
    nearest; a number pins it to that band.

    Returns {tex, metrics, fit, attempts, warnings}. Always returns a usable
    document: if the target is never hit, the closest attempt is returned with
    a warning rather than failing, since a slightly-off CV beats no CV.
    """
    warnings: List[str] = []
    target = None if target_pages in ("auto", None) else float(target_pages)
    max_attempts = int(config.get("PAGE_FIT_MAX_ATTEMPTS", 3))
    timeout = float(config.get("PAGE_FIT_COMPILE_TIMEOUT", 120))

    best = {"tex": tex, "metrics": None, "fit": None, "distance": None}
    current_tex = tex

    for attempt in range(1, max_attempts + 1):
        result = await compile_tex(current_tex, engine=engine, template_id=template_id, timeout=timeout)

        if not result.ok:
            # Can't measure — stop trying. The document may still compile fine
            # for the user; this loop is refinement, not a gate.
            detail = result.error_message or "compile failed"
            print(f"[LLM_BRAIN] Page fit: {detail} — skipping page fitting")
            warnings.append(f"page fitting skipped: {detail}")
            break

        try:
            metrics = measure_pdf(result.pdf_bytes, page_count_hint=result.page_count)
        except Exception as exc:
            print(f"[LLM_BRAIN] Page fit: could not measure PDF ({exc}) — skipping")
            warnings.append(f"page fitting skipped: could not measure PDF ({type(exc).__name__})")
            break

        warnings.extend(metrics.notes)
        fit = classify(metrics.length, target, pages=metrics.pages)
        print(
            f"[LLM_BRAIN] Page fit attempt {attempt}: {metrics.pages} page(s), "
            f"fill={metrics.fill_ratio:.2f}, length={metrics.length:.2f} → {fit['reason']}"
        )

        distance = abs(metrics.length - fit["band"])
        if best["distance"] is None or distance < best["distance"]:
            best = {"tex": current_tex, "metrics": metrics, "fit": fit, "distance": distance}

        if fit["ok"]:
            return {
                "tex": current_tex,
                "metrics": metrics,
                "fit": fit,
                "attempts": attempt,
                "warnings": warnings,
            }

        # Once auto has picked a band, hold it — otherwise the loop can chase a
        # moving target, condensing toward 1.0 then expanding back toward 1.5.
        if target is None:
            target = fit["band"]
            print(f"[LLM_BRAIN] Page fit: auto-selected {target} page target")

        if attempt == max_attempts:
            break

        adjust_prompt = build_page_fit_prompt(
            action=fit["action"],
            current_length=metrics.length,
            target_length=fit["band"],
            delta=fit["delta"],
            generated_tex=current_tex,
            template_tex=template_tex,
            pages=metrics.pages,
            expected=expected_pages(fit["band"]),
            last_page_fill=metrics.fill_ratio,
        )
        system_prompt = build_system_prompt(
            template_id=template_id,
            has_experience=True,
            has_education=True,
            target_pages=fit["band"],
        )
        adjusted = await call_llm_async(system_prompt, adjust_prompt)
        if not _has_valid_tex(adjusted):
            print("[LLM_BRAIN] Page fit: adjustment returned no valid LaTeX — stopping")
            warnings.append("page fitting stopped: adjustment produced invalid LaTeX")
            break
        current_tex = _finalize(adjusted, template_tex)

    if best["metrics"] is not None and not (best["fit"] or {}).get("ok"):
        warnings.append(
            f"could not hit the {best['fit']['band']} page target after {max_attempts} "
            f"attempt(s); returning closest result at {best['metrics'].length:.2f} pages"
        )

    return {
        "tex": best["tex"],
        "metrics": best["metrics"],
        "fit": best["fit"],
        "attempts": max_attempts,
        "warnings": warnings,
    }


# ── Core Orchestrator ─────────────────────────────────────────────────────────

async def generate_cv(
    user_profile: UserProfile,
    selected_repos: List[RepoDetail],
    template_id: str = "Jake_s_Resume__3_",
    target_role: str = "",
    target_pages="auto",
    latex_template: Optional[str] = None,
) -> dict:
    """
    Main CV generation pipeline:
    1. Fetch template (or use provided one)
    2. Build prompts
    3. Call LLM
    4. Validate → retry if needed
    5. Sanitize + preamble-swap
    6. LLM structure review against the template → repair if needed
    7. Compile → measure → expand/condense to hit 1 / 1.5 / 2 pages
    8. Return result
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
    # Ground-truth macro signatures parsed from the template itself, so the
    # LLM is told real arities rather than the registry's hand-written text.
    template_arity = extract_macro_arity(template_tex)
    macro_signatures = describe_macro_signatures(template_arity)

    system_prompt = build_system_prompt(
        template_id=template_id,
        has_experience=has_experience,
        has_education=has_education,
        macro_signatures=macro_signatures,
        target_pages=target_pages,
    )

    print(
        f"[LLM_BRAIN] Template: {template_id}, Engine: {engine}, "
        f"Repos: {len(selected_repos)}, Has exp: {has_experience}, "
        f"Has edu: {has_education}, Template size: {len(template_tex)} chars"
    )

    # ── Step 4: Call LLM (attempt 1) ──────────────────────────────────────
    edited_tex = await call_llm_async(system_prompt, user_prompt)

    # DEBUG: dump the raw section headers the LLM produced, to diagnose validation
    import re as _re
    for _m in _re.findall(r"\\section\*?\{[^}]*\}", edited_tex or ""):
        print(f"[LLM_BRAIN][DEBUG] section header: {_m!r}")

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
            retry_tex = await call_llm_async(system_prompt, retry_prompt)
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

    warnings: List[str] = []

    # ── Step 8b: Macro arity gate (deterministic, pre-compile) ────────────
    # A macro called with too few mandatory arguments is ALWAYS a fatal
    # compile error, and TeX reports it misleadingly. Catch and repair it here
    # rather than paying for a compile round-trip to find out.
    edited_tex, arity_problems = await enforce_macro_arity(
        edited_tex, template_tex, template_id
    )
    if arity_problems:
        warnings.append(
            f"{len(arity_problems)} macro call(s) still have the wrong argument count "
            "and will likely fail to compile: "
            + "; ".join(
                f"\\{p['macro']} (line {p['line']}) needs {p['expected']}, got {p['found']}"
                for p in arity_problems[:5]
            )
        )

    # ── Step 9: LLM structure review against the template ─────────────────
    # output_validator checks that required things are PRESENT; this checks
    # that what is present is structurally correct for this specific template
    # (invented macros, damaged preamble, unbalanced environments) — not
    # practical to express as regex across eight different templates.
    structure_review = None
    if config.get("ENABLE_STRUCTURE_REVIEW"):
        structure_review = await run_structure_review(template_id, template_tex, edited_tex)
        blocking = structure_review.get("blocking_issues") or []
        if blocking:
            print(f"[LLM_BRAIN] Structure review found {len(blocking)} blocking issue(s) — repairing")
            repaired = await apply_structure_repair(
                template_id, template_tex, edited_tex, blocking
            )
            if repaired:
                edited_tex = repaired
                # Re-check that the repair didn't strip out required content.
                recheck = validate_output(edited_tex, user_profile, has_experience, has_education)
                if not recheck.passed:
                    warnings.append(
                        "structure repair introduced completeness gaps: "
                        + ", ".join(recheck.failures)
                    )
            else:
                warnings.append("structural issues found but repair failed; returning original")
        elif structure_review.get("issues"):
            warnings.append(
                f"{len(structure_review['issues'])} minor structural note(s) from review"
            )

    # ── Step 10: Fit the document to 1 / 1.5 / 2 pages ────────────────────
    page_metrics = None
    page_fit = None
    if config.get("ENABLE_PAGE_FIT"):
        fit_result = await fit_to_page_target(
            tex=edited_tex,
            template_tex=template_tex,
            template_id=template_id,
            engine=engine,
            target_pages=target_pages,
        )
        edited_tex = fit_result["tex"]
        page_metrics = fit_result["metrics"]
        page_fit = fit_result["fit"]
        warnings.extend(fit_result["warnings"])

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

    if page_metrics is not None:
        summary = (
            f"Resume generated: {page_metrics.length:.2f} pages "
            f"({page_metrics.pages} physical, last page {page_metrics.fill_ratio:.0%} full)"
        )
        if page_fit and page_fit.get("ok"):
            summary += f", on the {page_fit['band']} page target."
        elif page_fit:
            summary += f", closest achievable to the {page_fit['band']} page target."
    else:
        summary = "Resume generated with template-aware prompting and completeness validation."

    return {
        "ok": True,
        "tex": edited_tex,
        "engine": engine,
        "template_id": template_id,
        "summary": summary,
        "pages": page_metrics.to_dict() if page_metrics else None,
        "page_fit": page_fit,
        "structure_review": structure_review,
        "warnings": warnings,
    }
