"""
API routes for LLM_BRAIN CV generation service.
"""

import traceback

from fastapi import APIRouter, HTTPException
import httpx

from app.models import GenerateCvRequest
from app.service.latex_generator_services import generate_cv
from app.prompts.template_registry import list_templates_summary

router = APIRouter()


@router.get("/health")
def health():
    """
    Health check.

    Reports which refinement features the RUNNING build has, so it is possible
    to tell at a glance whether a deployed service actually picked up a change
    rather than still running an older image.
    """
    from app.config.serverConfig import Server_Credentials
    from app.service.page_metrics import ALLOWED_LENGTHS

    cfg = Server_Credentials()
    return {
        "ok": True,
        "service": "LLM Brain",
        "build": "2026-07-29-structural-gate-v3",
        "features": {
            "macro_arity_gate": True,
            "macro_arity_final_gate": True,
            "brace_env_balance_check": True,
            "structure_review": bool(cfg.get("ENABLE_STRUCTURE_REVIEW")),
            "page_fit": bool(cfg.get("ENABLE_PAGE_FIT")),
            "page_bands": list(ALLOWED_LENGTHS),
        },
    }


@router.get("/api/templates")
def list_templates():
    """
    List all supported templates with their compilation engine.
    Frontend can use this to show available templates and know
    which engine to pass to CV_BUILDER for compilation.
    """
    templates = list_templates_summary()
    return {"ok": True, "templates": templates}


@router.post("/api/generate-cv")
async def generate_cv_endpoint(req: GenerateCvRequest):
    """
    Generate a CV by filling a LaTeX template with user data via LLM.
    
    Accepts:
      - user_profile: User's personal/professional data
      - selected_repos: GitHub repositories to extract project info from
      - template_id: Which template to use (e.g., "Jake_s_Resume__3_")
      - target_role: Optional target job role for ATS optimization
      - target_pages: "auto" (default), 1, 1.5 or 2. "auto" lets the content
        decide, then snaps to the nearest of those bands.
      - latex_template: Optional raw LaTeX (backward compat — if provided, skip fetch)

    Returns:
      - ok: bool
      - tex: The filled LaTeX string
      - engine: The compiler to use (pdflatex/xelatex/lualatex)
      - template_id: Which template was used
      - summary: Human-readable status
      - pages: {pages, fill_ratio, length, measured} — measured document length
      - page_fit: {ok, band, action, reason} — whether it hit the page target
      - structure_review: LLM audit of the tex against the template
      - warnings: non-fatal problems worth surfacing to the user
    """
    try:
        result = await generate_cv(
            user_profile=req.user_profile,
            selected_repos=req.selected_repos,
            template_id=req.template_id or "Jake_s_Resume__3_",
            target_role=req.target_role or "",
            # "auto" is meaningful — don't collapse it with `or`.
            target_pages=req.target_pages if req.target_pages is not None else "auto",
            latex_template=req.latex_template,
        )
        return result

    except ValueError as ve:
        print(f"[LLM_BRAIN] ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except (httpx.HTTPStatusError, httpx.RequestError) as he:
        print(f"[LLM_BRAIN] CV_BUILDER request error: {type(he).__name__}: {he}")
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch the LaTeX template from CV_BUILDER. Is the compiler service reachable?",
        )
    except Exception as err:
        # Don't echo raw internals to the client — they can carry API keys,
        # internal URLs and stack detail. Log fully, return a generic message.
        traceback.print_exc()
        print(f"[LLM_BRAIN] Unhandled exception: {type(err).__name__}: {err}")
        raise HTTPException(
            status_code=500,
            detail="CV generation failed due to an internal error. Check the CV_BRAIN service logs.",
        )
