"""
Page metrics — measure how long a compiled CV actually is.

A PDF only has an integer page count, so "1.5 pages" cannot be read off it
directly. What the user means by 1.5 is "two pages, the second about half
full", so the useful measurement is:

    pages           how many physical pages
    fill_ratio      how much of the LAST page carries content (0.0 - 1.0)

length = (pages - 1) + fill_ratio

That gives a continuous number which can be snapped to the allowed 1.0 / 1.5 /
2.0 bands. fill_ratio is derived from the lowest text baseline on the final
page relative to the page's usable height.
"""

import math
import os
from dataclasses import dataclass, field
from typing import List, Optional

# Allowed document lengths, in pages.
#
# Default is 1 or 2 whole pages: a resume that stops a quarter of the way down
# page 2 looks like an accident. 1.5 is still selectable by asking for it
# explicitly (target_pages=1.5) or via PAGE_LENGTH_BANDS.
def _load_bands() -> tuple:
    raw = os.getenv("PAGE_LENGTH_BANDS", "1,2")
    try:
        bands = tuple(sorted({float(x) for x in raw.split(",") if x.strip()}))
    except ValueError:
        bands = (1.0, 2.0)
    return bands or (1.0, 2.0)


ALLOWED_LENGTHS = _load_bands()

# How far a measured length may sit from a band and still count as that band.
# +/-0.12 page is roughly +/-5 lines of text — tight enough that the result
# visually reads as "one page" / "a page and a half" / "two pages", loose
# enough that the loop terminates.
BAND_TOLERANCE = 0.12

# A last page emptier than this is a stub — it reads as an accident rather
# than a deliberate half page.
MIN_LAST_PAGE_FILL = 0.10


@dataclass
class PageMetrics:
    """Measured length of a compiled document."""

    pages: int
    fill_ratio: float
    length: float
    measured: bool = True
    # Set when the fill ratio could not be measured and was assumed.
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pages": self.pages,
            "fill_ratio": round(self.fill_ratio, 3),
            "length": round(self.length, 2),
            "measured": self.measured,
            "notes": list(self.notes),
        }


def nearest_band(length: float) -> float:
    """Snap a measured length to the closest allowed band."""
    return min(ALLOWED_LENGTHS, key=lambda b: abs(b - length))


def expected_pages(band: float) -> int:
    """
    Physical sheets a band occupies. 1.0 -> 1, 1.5 -> 2, 2.0 -> 2.
    Computed rather than hardcoded so custom bands work.
    """
    return max(1, math.ceil(band - 1e-9))


# Back-compat alias for the fixed default bands.
EXPECTED_PAGES = {b: expected_pages(b) for b in ALLOWED_LENGTHS}


def classify(length: float, target: Optional[float] = None, pages: Optional[int] = None) -> dict:
    """
    Decide whether a measured length is acceptable, and if not, which way the
    content needs to move.

    target=None means "auto": accept whichever band the content is already
    closest to. Otherwise the document must land on the requested band.

    `pages` is the physical sheet count. When supplied it is enforced against
    the band, which is what stops an orphan stub page being reported as a
    tidy single-page CV.

    Returns {ok, band, target, delta, action, reason}. `action` is one of
    "none", "expand", "condense" — what the LLM should do next.
    """
    # Auto-selection picks the band needing the LEAST change.
    #
    # Previously this filtered candidates to bands matching the current
    # physical page count, which was wrong: a 2-page document whose second page
    # is 9% full (length 1.09) had 1.0 excluded, so it chose "expand 0.41
    # pages" over "condense 0.09". Expanding means inventing ~18 lines of
    # content that may not exist, so the loop failed and returned the stub.
    # Trimming toward the nearest band is nearly always the achievable move.
    band = target if target is not None else nearest_band(length)

    delta = length - band

    if pages is not None and pages != expected_pages(band):
        # Physically the wrong number of sheets for this band. Direction is
        # decided by the sheet count, not the fractional length: a 2-page
        # document with a near-empty second page is "too long" even though its
        # measured length is barely over 1.
        too_many = pages > expected_pages(band)
        last_page_fill = length - (pages - 1)
        reason = f"{pages} physical page(s) but the {band} page band needs {expected_pages(band)}"
        # Only call it an orphan when the final page really is nearly empty —
        # a full overflow page is a different problem from a stub.
        if too_many and last_page_fill < MIN_LAST_PAGE_FILL:
            reason += f"; the last page carries only {last_page_fill * 100:.0f}% content (orphan page)"
        return {
            "ok": False,
            "band": band,
            "target": target,
            "delta": round(delta, 3),
            "action": "condense" if too_many else "expand",
            "reason": reason,
        }

    # Epsilon: a delta of exactly BAND_TOLERANCE lands just outside it in
    # binary floating point (1.62 - 1.5 == 0.12000000000000011).
    if abs(delta) <= BAND_TOLERANCE + 1e-9:
        return {
            "ok": True,
            "band": band,
            "target": target,
            "delta": round(delta, 3),
            "action": "none",
            "reason": f"length {length:.2f} is within {BAND_TOLERANCE} of the {band} page band",
        }

    action = "condense" if delta > 0 else "expand"
    return {
        "ok": False,
        "band": band,
        "target": target,
        "delta": round(delta, 3),
        "action": action,
        "reason": (
            f"length {length:.2f} pages is {abs(delta):.2f} page "
            f"{'over' if delta > 0 else 'under'} the {band} page target"
        ),
    }


# A baseline carrying fewer than this many characters is treated as a stray
# glyph rather than a line of content. Jake's template renders a `$|$`
# separator whose text matrix reports y=0 — a 2-character speck at the very
# bottom of the page that otherwise made EVERY page measure as 100% full.
_MIN_BASELINE_CHARS = 3


def _collect_baselines(page) -> dict:
    """Map baseline y -> number of non-space characters drawn at that y."""
    baselines: dict = {}

    def visitor(text, cm, tm, font_dict, font_size):
        if not text or not text.strip():
            return
        try:
            y = round(float(tm[5]), 1)
        except (TypeError, IndexError, ValueError):
            return
        baselines[y] = baselines.get(y, 0) + len(text.strip())

    page.extract_text(visitor_text=visitor)
    return baselines


def _fill_ratio_from_page(page) -> Optional[float]:
    """
    Fraction of a page's usable height that carries text.

    Measured as (top baseline - bottom baseline) / (top baseline - bottom
    margin), where the bottom margin is inferred from the top one. Deriving the
    top reference from the actual first line of text — rather than assuming a
    fixed margin — self-calibrates to each template's geometry, which varies
    widely across the eight templates here.

    Returns None when nothing measurable is found (e.g. an all-graphics page).
    """
    try:
        page_height = float(page.mediabox.height)
    except Exception:
        return None
    if page_height <= 0:
        return None

    try:
        baselines = _collect_baselines(page)
    except Exception:
        return None

    # Keep only baselines inside the page that carry real text.
    ys = {
        y: n
        for y, n in baselines.items()
        if 0 <= y <= page_height and n >= _MIN_BASELINE_CHARS
    }
    if not ys:
        return None

    total_chars = sum(ys.values())
    ordered = sorted(ys)

    # Drop isolated specks near the bottom: a baseline far below the next one
    # up that carries a negligible share of the page's text is not content.
    while len(ordered) > 1:
        gap = ordered[1] - ordered[0]
        share = ys[ordered[0]] / total_chars if total_chars else 0
        if gap > page_height * 0.15 and share < 0.02:
            ordered.pop(0)
        else:
            break

    lowest, highest = ordered[0], ordered[-1]

    # Infer the bottom margin from the top one; most resume templates are
    # roughly symmetric vertically.
    top_margin = max(0.0, page_height - highest)
    usable_height = highest - top_margin
    if usable_height <= 0:
        return None

    ratio = (highest - lowest) / usable_height
    # Content can legitimately run into the bottom margin.
    return max(0.0, min(1.0, ratio))


def measure_pdf(pdf_bytes: bytes, page_count_hint: Optional[int] = None) -> PageMetrics:
    """
    Measure a compiled PDF.

    `page_count_hint` is CV_BUILDER's X-Page-Count header when available — it
    comes straight from the latexmk log and is authoritative, so it wins over
    anything parsed here.

    Degrades in stages rather than raising: if pypdf is missing or the PDF is
    unreadable, falls back to the hint (assuming a full last page), and only
    gives up entirely if there is nothing at all to go on.
    """
    notes: List[str] = []

    try:
        from pypdf import PdfReader
    except ImportError:
        notes.append("pypdf not installed — fill ratio unavailable, assumed full last page")
        if page_count_hint:
            return PageMetrics(
                pages=page_count_hint,
                fill_ratio=1.0,
                length=float(page_count_hint),
                measured=False,
                notes=notes,
            )
        raise RuntimeError("cannot measure PDF: pypdf missing and no page count hint")

    import io

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = len(reader.pages)
    except Exception as exc:
        notes.append(f"could not parse PDF ({type(exc).__name__}) — falling back to page count hint")
        if page_count_hint:
            return PageMetrics(
                pages=page_count_hint,
                fill_ratio=1.0,
                length=float(page_count_hint),
                measured=False,
                notes=notes,
            )
        raise

    if page_count_hint and page_count_hint != pages:
        # Trust latexmk over our own parse, but say so.
        notes.append(f"page count hint ({page_count_hint}) differs from parsed ({pages}); using hint")
        pages = page_count_hint

    if pages <= 0:
        raise RuntimeError("compiled PDF reports zero pages")

    fill = _fill_ratio_from_page(reader.pages[min(pages, len(reader.pages)) - 1])
    if fill is None:
        notes.append("no measurable text on the last page — assumed full")
        fill = 1.0

    return PageMetrics(
        pages=pages,
        fill_ratio=fill,
        length=(pages - 1) + fill,
        measured=True,
        notes=notes,
    )
