"""
Output Validator — checks LLM-generated LaTeX for completeness.
Ensures the resume is not half-cooked: all sections present, full page,
document properly terminated, user data actually injected.
"""

import json
import re
from app.models import UserProfile, ValidationResult


def _check_section_present(tex: str, section_name: str) -> bool:
    """Check if a section with the given name exists and has content after it."""
    # Match common section patterns across all templates
    patterns = [
        rf"\\section\{{{section_name}\}}",
        rf"\\cvsection\{{{section_name}\}}",
        rf"\\subsection\{{{section_name}\}}",
    ]
    for pattern in patterns:
        if re.search(pattern, tex, re.IGNORECASE):
            return True
    return False


def _count_content_lines(tex: str) -> int:
    """
    Count meaningful content lines inside \\begin{document}...\\end{document}.
    Excludes blank lines, comments, and pure-whitespace lines.
    """
    begin_idx = tex.find(r"\begin{document}")
    end_idx = tex.find(r"\end{document}")

    if begin_idx < 0 or end_idx < 0:
        return 0

    body = tex[begin_idx:end_idx]
    lines = body.split("\n")
    content_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("%"):
            content_lines += 1

    return content_lines


def _check_has_bullet_content(tex: str) -> bool:
    """Check that the resume has actual bullet points with real content."""
    # Match \resumeItem{...}, \item{...}, \item ..., \cvitem{...}, etc.
    bullet_patterns = [
        r"\\resumeItem\{.{10,}\}",       # Jake/Anubhav style: at least 10 chars
        r"\\item\{.{10,}\}",             # Awesome CV style
        r"\\item\s+.{10,}",             # Standard \item with text
        r"\\cvitem\{[^}]+\}\{.{10,}\}", # ModernCV style
    ]
    total_bullets = 0
    for pattern in bullet_patterns:
        total_bullets += len(re.findall(pattern, tex))

    return total_bullets >= 3  # at least 3 meaningful bullets in the whole resume


def validate_output(
    tex: str,
    user_profile: UserProfile,
    has_experience: bool,
    has_education: bool,
) -> ValidationResult:
    """
    Validate LLM-generated LaTeX for completeness.
    
    Checks:
    - Document structure (\\documentclass, \\begin/end{document})
    - Not truncated (ends with \\end{document})
    - User's name is present
    - All applicable sections exist
    - Minimum content line count (for full page)
    - Has meaningful bullet content
    
    Returns a ValidationResult with pass/fail and list of failures.
    """
    checks = {}

    # ── Structural checks ─────────────────────────────────────────────────
    checks["has_documentclass"] = r"\documentclass" in tex
    checks["has_begin_document"] = r"\begin{document}" in tex
    checks["has_end_document"] = r"\end{document}" in tex

    # Check not truncated — the document should end with \end{document}
    # (possibly followed by whitespace/comments)
    stripped_end = tex.strip()
    checks["not_truncated"] = stripped_end.endswith(r"\end{document}")

    # ── User data presence ────────────────────────────────────────────────
    if user_profile.name:
        # Check either first or last name appears (case-insensitive)
        name_parts = user_profile.name.lower().split()
        checks["has_user_name"] = any(part in tex.lower() for part in name_parts if len(part) > 1)
    else:
        checks["has_user_name"] = True  # no name to check

    # Check for placeholder leak (template echo instead of substitution)
    checks["no_placeholder_leak"] = True
    user_profile_str = json.dumps(user_profile.dict()).lower()
    known_placeholders = [
        "jake ryan", "sourabh bajaj", "southwestern university", "blinn college",
        "gitlytics", "simple paintball", "texas a&m university", "texas a\\&m university",
        "zachary deedy", "claud d. park", "danny phang", "john doe"
    ]
    for placeholder in known_placeholders:
        if placeholder in tex.lower() and placeholder not in user_profile_str:
            checks["no_placeholder_leak"] = False
            print(f"[LLM_BRAIN] Validation failed: Found placeholder '{placeholder}' in generated LaTeX, which was not in user profile.")
            break

    # ── Section presence checks ───────────────────────────────────────────
    if has_education:
        checks["has_education_section"] = _check_section_present(tex, "Education")
    
    if has_experience:
        checks["has_experience_section"] = (
            _check_section_present(tex, "Experience")
            or _check_section_present(tex, "Work Experience")
        )

    # Projects should almost always be present (repos are selected)
    checks["has_projects_section"] = (
        _check_section_present(tex, "Projects")
        or _check_section_present(tex, "Project")
        or _check_section_present(tex, "Personal Projects")
        or _check_section_present(tex, "Selected Projects")
        # Some templates use experience entries for projects
        or r"\resumeProjectHeading" in tex
        or r"\runsubsection" in tex
    )

    checks["has_skills_section"] = (
        _check_section_present(tex, "Skills")
        or _check_section_present(tex, "Technical Skills")
        or _check_section_present(tex, "Computer Skills")
        or r"\cvtag{" in tex
        or r"\cvskill{" in tex
    )

    # ── Content density checks ────────────────────────────────────────────
    content_lines = _count_content_lines(tex)
    # A full-page resume typically has 50-80 content lines.
    # Minimum 30 lines ensures it's not a near-empty document.
    checks["min_content_lines"] = content_lines >= 30

    checks["has_bullet_content"] = _check_has_bullet_content(tex)

    # ── Aggregate result ──────────────────────────────────────────────────
    passed = all(checks.values())
    failures = [k for k, v in checks.items() if not v]

    if failures:
        print(f"[LLM_BRAIN] Validation FAILED: {failures} (content lines: {content_lines})")
    else:
        print(f"[LLM_BRAIN] Validation PASSED (content lines: {content_lines})")

    return ValidationResult(passed=passed, failures=failures, checks=checks)
