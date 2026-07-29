"""
Prompts for the two post-generation refinement passes:

  1. Structural review — does the generated .tex actually respect the template
     it was supposed to fill?
  2. Page fitting — expand or condense the content to hit a page target.

Both are repair passes over an existing document, not fresh generation, so
they emphasise "change only what is necessary".
"""

from app.prompts.template_registry import get_template_context


def build_structure_review_prompt(template_id: str, template_tex: str, generated_tex: str) -> tuple:
    """
    Ask the LLM to audit the generated document against the template.

    Returns (system_prompt, user_prompt). The model is asked for strict JSON so
    the result can be acted on programmatically rather than eyeballed.
    """
    template_context = get_template_context(template_id)

    system_prompt = """You are a LaTeX resume STRUCTURE AUDITOR. You are given an original LaTeX template and a filled-in version of it. Your job is to judge whether the filled version correctly respects the template's structure.

You are NOT rewriting the document. You are only reporting problems.

Check for:
1. MACRO MISUSE — macros invented that the template never defined, template macros renamed, or macros called with the wrong number of arguments.
2. PREAMBLE DAMAGE — \\documentclass, \\usepackage, \\newcommand/\\renewcommand, geometry or style settings that were altered, dropped, or added.
3. STRUCTURAL BREAKAGE — unbalanced braces, unclosed environments, list environments opened but never closed, \\begin without matching \\end.
4. EMPTY CONSTRUCTS — sections or list environments with no items inside; these are fatal in several of these templates.
5. SECTION SANITY — sections that the template's design does not support, or content placed in a section where it does not belong.
6. PLACEHOLDER LEAK — sample data from the template (names, universities, project names) still present.
7. TRUNCATION — document does not run cleanly from \\documentclass to \\end{document}.

Severity:
- "fatal"   — will fail to compile, or produces a visibly broken document.
- "major"   — compiles, but the structure diverges from the template's design.
- "minor"   — cosmetic or stylistic only.

Respond with STRICT JSON and nothing else. No markdown fences, no commentary:

{
  "structure_ok": true|false,
  "issues": [
    {"severity": "fatal|major|minor", "location": "short snippet or macro name", "problem": "what is wrong", "fix": "what to change"}
  ],
  "summary": "one sentence"
}

Set "structure_ok" to false if there is any fatal or major issue. An empty issues list with structure_ok true is a perfectly valid answer when the document is clean."""

    user_prompt = f"""TEMPLATE RULES FOR THIS TEMPLATE ({template_id}):
{template_context}

=========================================
ORIGINAL TEMPLATE:
=========================================
{template_tex}

=========================================
GENERATED DOCUMENT TO AUDIT:
=========================================
{generated_tex}

Audit the generated document against the original template. Respond with the JSON object only."""

    return system_prompt, user_prompt


def build_structure_repair_prompt(
    template_id: str,
    template_tex: str,
    generated_tex: str,
    issues: list,
) -> str:
    """Ask the LLM to fix the structural issues the audit found."""
    issue_lines = "\n".join(
        f"  - [{i.get('severity', '?')}] {i.get('location', '')}: "
        f"{i.get('problem', '')} → FIX: {i.get('fix', '')}"
        for i in issues
    )

    return f"""Your previous LaTeX output has STRUCTURAL PROBLEMS that must be fixed.

PROBLEMS FOUND:
{issue_lines}

Fix every problem listed above. Rules:
- Change ONLY what is needed to fix these problems. Do not rewrite content that is fine.
- Do not remove the candidate's real data.
- Keep using only macros the template defines.
- Return the COMPLETE LaTeX document, \\documentclass through \\end{{document}}.
- Raw LaTeX only. No markdown fences, no commentary.

=========================================
ORIGINAL TEMPLATE (authoritative structure):
=========================================
{template_tex}

=========================================
DOCUMENT TO FIX:
=========================================
{generated_tex}
"""


def build_macro_arity_repair_prompt(
    template_tex: str,
    generated_tex: str,
    problems_text: str,
    signatures: str,
) -> str:
    """
    Repair macro calls that supply too few mandatory arguments.

    Deterministically detected, so the instruction can be blunt and specific
    rather than asking the model to go looking for the problem.
    """
    return f"""Your LaTeX output calls template macros with the WRONG NUMBER OF ARGUMENTS. This is a FATAL compile error — TeX swallows whatever follows the incomplete call and dies with a misleading message such as "Missing number, treated as zero".

EXACT PROBLEMS FOUND:
{problems_text}

THE TEMPLATE'S TRUE MACRO SIGNATURES (authoritative):
{signatures}

Fix every listed call so it supplies exactly the required number of {{...}} groups.
- If a macro needs 2 arguments and you only wrote 1, split your content sensibly:
  a short bold label in the first group, the descriptive text in the second.
  Example: \\resumeItem{{Project Overview}} → \\resumeItem{{Project Overview}}{{Built a ... that ...}}
- Do NOT delete the bullet to dodge the problem, and do NOT invent facts to pad
  the extra argument — re-use the wording already present.
- Change nothing else.

Return the COMPLETE LaTeX document, \\documentclass through \\end{{document}}.
Raw LaTeX only. No markdown fences, no commentary.

=========================================
DOCUMENT TO FIX:
=========================================
{generated_tex}
"""


def build_page_fit_prompt(
    action: str,
    current_length: float,
    target_length: float,
    delta: float,
    generated_tex: str,
    template_tex: str,
) -> str:
    """
    Ask the LLM to expand or condense the document to hit a page target.

    `delta` is how far off we are in pages; it is converted into a concrete
    line budget, because "make it a bit shorter" is far less actionable to an
    LLM than "remove about 8 lines".
    """
    # ~45 usable text lines per page is a fair average across these templates.
    LINES_PER_PAGE = 45
    lines_off = max(1, round(abs(delta) * LINES_PER_PAGE))

    if action == "condense":
        instruction = f"""The document is currently {current_length:.2f} pages and must become {target_length} pages.
It is TOO LONG by roughly {lines_off} lines of text.

Shorten it by approximately {lines_off} lines. In priority order:
1. Tighten wordy bullet points — same fact, fewer words. Cut filler like "responsible for", "worked on", "helped to".
2. Merge two closely-related bullets into one.
3. Drop the LEAST impressive bullet from the project or experience entry that has the most bullets.
4. Shorten the skills list by removing the most generic entries.

HARD CONSTRAINTS — violating any of these is a failure:
- Every project entry MUST still have its dedicated "Tech Stack:" bullet plus AT LEAST 3 description bullets.
- Do NOT delete an entire project, experience, or education entry.
- Do NOT drop a section that has real candidate data.
- Do NOT shrink fonts, margins, or spacing. Do NOT touch the preamble."""
    else:
        instruction = f"""The document is currently {current_length:.2f} pages and must become {target_length} pages.
It is TOO SHORT by roughly {lines_off} lines of text.

Lengthen it by approximately {lines_off} lines. In priority order:
1. Add technical depth to existing project bullets — architecture, design decisions, scale, specific technologies, measurable outcomes drawn from the README, commit messages or file tree already provided.
2. Add a further substantive bullet to the project or experience entry that currently has the fewest.
3. Expand the skills section into more specific, better-organised categories.
4. Add a brief professional summary near the top IF the template supports one and the candidate provided the material for it.

HARD CONSTRAINTS — violating any of these is a failure:
- Do NOT invent facts. No fabricated employers, dates, metrics, or technologies the candidate never mentioned. Draw only on data already supplied.
- Do NOT pad with filler sentences that carry no information.
- Do NOT enlarge fonts, margins, or spacing. Do NOT touch the preamble.
- Do NOT repeat the same point in two bullets."""

    return f"""Adjust the length of this LaTeX resume.

{instruction}

Keep the template's structure and macros exactly as they are.
Return the COMPLETE LaTeX document, \\documentclass through \\end{{document}}.
Raw LaTeX only. No markdown fences, no commentary.

=========================================
TEMPLATE (authoritative structure — do not deviate):
=========================================
{template_tex}

=========================================
DOCUMENT TO ADJUST:
=========================================
{generated_tex}
"""
