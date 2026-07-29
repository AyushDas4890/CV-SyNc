"""
Compile client — asks CV_BUILDER to turn generated .tex into a PDF so the
generator can measure how long the document actually came out.

This is a measurement round-trip, not the user's download. The frontend still
compiles separately for the PDF it hands back to the user.
"""

from dataclasses import dataclass
from typing import Optional, List

import httpx

from app.config.serverConfig import Server_Credentials

config = Server_Credentials()


@dataclass
class CompileResult:
    ok: bool
    pdf_bytes: Optional[bytes] = None
    # From CV_BUILDER's X-Page-Count header. None on older builds that predate
    # it — callers fall back to parsing the PDF.
    page_count: Optional[int] = None
    log: str = ""
    errors: Optional[List[dict]] = None
    error_message: str = ""


async def compile_tex(
    tex: str,
    engine: str = "pdflatex",
    template_id: Optional[str] = None,
    timeout: float = 120.0,
) -> CompileResult:
    """
    POST the tex to CV_BUILDER /api/compile.

    Never raises for an unreachable or unhappy compiler — page fitting is a
    refinement step, so a failure here must degrade to "couldn't measure"
    rather than sink an otherwise good generation.
    """
    url = f"{config['CV_BUILDER_URL'].rstrip('/')}/api/compile"
    payload = {"tex": tex, "engine": engine}
    if template_id:
        payload["templateId"] = template_id

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
    except httpx.RequestError as exc:
        return CompileResult(
            ok=False,
            error_message=f"CV_BUILDER unreachable: {type(exc).__name__}",
        )

    if resp.status_code == 200:
        raw_count = resp.headers.get("X-Page-Count")
        page_count = None
        if raw_count:
            try:
                page_count = int(raw_count)
            except ValueError:
                page_count = None
        return CompileResult(ok=True, pdf_bytes=resp.content, page_count=page_count)

    # 422 carries the LaTeX log and parsed errors; other codes carry JSON too.
    log, errors = "", None
    try:
        data = resp.json()
        log = data.get("log", "") or ""
        errors = data.get("errors")
    except Exception:
        log = resp.text[:4000]

    return CompileResult(
        ok=False,
        log=log,
        errors=errors,
        error_message=f"CV_BUILDER returned {resp.status_code}",
    )
