"""
API routes for LLM_BRAIN CV generation service.
"""

from fastapi import APIRouter, HTTPException
import httpx

from app.models import GenerateCvRequest
from app.service.latex_generator_services import generate_cv
from app.prompts.template_registry import list_templates_summary

router = APIRouter()


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "service": "LLM Brain"}


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
      - target_pages: Number of pages (default 1)
      - latex_template: Optional raw LaTeX (backward compat — if provided, skip fetch)
    
    Returns:
      - ok: bool
      - tex: The filled LaTeX string
      - engine: The compiler to use (pdflatex/xelatex/lualatex)
      - template_id: Which template was used
      - summary: Human-readable status
    """
    try:
        result = await generate_cv(
            user_profile=req.user_profile,
            selected_repos=req.selected_repos,
            template_id=req.template_id or "Jake_s_Resume__3_",
            target_role=req.target_role or "",
            target_pages=req.target_pages or 1,
            latex_template=req.latex_template,
        )
        return result

    except ValueError as ve:
        print(f"[LLM_BRAIN] ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except httpx.HTTPStatusError as he:
        print(f"[LLM_BRAIN] CV_BUILDER HTTP error: {he}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch template from CV_BUILDER: {he}",
        )
    except Exception as err:
        print(f"[LLM_BRAIN] Exception: {err}")
        raise HTTPException(status_code=500, detail=str(err))
