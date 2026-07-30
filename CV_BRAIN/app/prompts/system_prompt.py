"""
System prompt builder — generates a template-aware, completeness-enforced
system prompt for the LLM based on the selected template and user data context.
"""

from app.prompts.template_registry import get_template_context, get_template_metadata


def _hyperlink_rule(template_id: str) -> str:
    """
    Render the HYPERLINKS rule for this template.

    Not every template loads hyperref. dphang does not, so \\href there is a
    fatal "Undefined control sequence" — and because the preamble is restored
    from the original template before compiling, the model cannot fix it by
    adding \\usepackage{hyperref} either. The rule has to change, not the
    document.
    """
    meta = get_template_metadata(template_id) or {}
    if meta.get("supports_hyperlinks", True):
        return (
            "For project GitHub links, use \\\\href{{URL}}{{\\\\underline{{GitHub}}}} "
            "where URL contains raw underscores (NOT \\\\_ or %5F). hyperref "
            "handles underscores in URLs natively."
        )
    return (
        "**THIS TEMPLATE HAS NO HYPERREF.** \\\\href, \\\\url and \\\\nolinkurl are "
        "UNDEFINED here and each one is a FATAL compile error. Write every link "
        "as plain visible text instead — `github.com/user/repo`, "
        "`linkedin.com/in/id`, the bare email address. Do NOT add "
        "\\\\usepackage{{hyperref}} to fix this: the preamble is replaced with the "
        "template's original before compiling, so your addition is discarded and "
        "only the broken \\\\href calls remain."
    )


def _tech_stack_rule() -> str:
    """
    Render the tech-stack bullet rule without naming a macro that may not exist.

    This rule used to spell its example with \\resumeItem, which is defined ONLY
    in Jake's and Anubhav's templates. Generating with AltaCV or PlushCV copied
    the example literally and died with "Undefined control sequence" — the
    prompt itself was the bug. The example is now written against whatever
    bullet macro this template actually has.
    """
    return (
        "Write it using **this template's own bullet macro**, taken from the "
        "AVAILABLE MACROS list and the EXACT MACRO SIGNATURES block — never a "
        "bullet macro borrowed from a different template.\n"
        "    - if this template's bullet is plain \\\\item → "
        "\\\\item \\\\textbf{{Tech Stack:}} React, Node.js, MongoDB, Docker\n"
        "    - if it is a ONE-argument macro (e.g. \\\\somebullet{{...}}) → "
        "\\\\somebullet{{\\\\textbf{{Tech Stack:}} React, Node.js, MongoDB, Docker}}\n"
        "    - if it is a TWO-argument macro (e.g. \\\\somebullet{{...}}{{...}}) → "
        "\\\\somebullet{{Tech Stack}}{{React, Node.js, MongoDB, Docker}}\n"
        "    Substitute the real macro name from THIS template. Never omit a "
        "mandatory argument to fit the pattern."
    )


def _page_budget_text(target_pages) -> str:
    """
    Render the PAGE BUDGET rule.

    'auto' means the content decides the length, so the model is told the
    permitted landing zones rather than one fixed number — the compile-measure
    loop afterwards is what actually pins it to a band.
    """
    if target_pages == "auto" or target_pages is None:
        return (
            "The finished resume MUST be exactly ONE page, ONE AND A HALF pages, or TWO pages "
            "— nothing in between and nothing longer. Judge from the amount of real candidate "
            "data provided which of those three is honest: sparse data means a well-filled single "
            "page, rich data (several roles plus several substantial projects) means two. "
            "'One and a half' means a full first page and a second page filled roughly halfway.\n"
            "    A page that trails off into blank white space after a few lines is a FAILURE, "
            "and so is a second page carrying only two or three stray lines"
        )

    target = float(target_pages)
    if target == 1.5:
        return (
            "The finished resume MUST be ONE AND A HALF pages: a completely full first page, "
            "and a second page filled roughly halfway (about 40-60% of its height).\n"
            "    A nearly-empty second page is a FAILURE"
        )
    plural = "s" if target != 1 else ""
    return (
        f"The finished resume MUST fill exactly {target:g} full page{plural} of content.\n"
        "    A resume with a few lines of content followed by blank white space is a FAILURE"
    )


def build_system_prompt(
    template_id: str,
    has_experience: bool,
    has_education: bool,
    target_pages=1,
    macro_signatures: str = "",
) -> str:
    """
    Build the full system prompt incorporating:
    1. Template-specific rules (macros, engine, header pattern)
    2. Completeness enforcement rules
    3. Conditional section logic
    4. Zero hallucination constraints
    """

    template_context = get_template_context(template_id)

    # Signatures parsed from the actual template source. These are ground
    # truth and override the hand-written registry text above, which has
    # drifted before — describing Anubhav's two-mandatory-argument
    # \\resumeItem as taking an optional label, which produced one-argument
    # calls and a fatal "Missing number, treated as zero" compile error.
    signature_block = ""
    if macro_signatures:
        signature_block = f"""
═══════════════════════════════════════════════════════════════════════════════
EXACT MACRO SIGNATURES FOR THIS TEMPLATE — AUTHORITATIVE
═══════════════════════════════════════════════════════════════════════════════

These were read directly from this template's source. Where anything above
disagrees with this list, THIS LIST WINS.

{macro_signatures}

Supply EXACTLY the number of mandatory {{...}} arguments shown. A macro called
with too few arguments silently swallows whatever follows it and produces a
fatal, confusing compile error. If a macro takes 2 arguments and you only have
one piece of information, still emit both groups — put the text in the first
and leave the second as a short meaningful value, never omit the braces.
"""

    return f"""You are a LaTeX template filler. You receive a LaTeX resume template and user data. Your ONLY job is to replace the sample/placeholder data in the template with the user's real data. You must preserve the EXACT structure, macros, and formatting of the template.

═══════════════════════════════════════════════════════════════════════════════
TEMPLATE-SPECIFIC RULES
═══════════════════════════════════════════════════════════════════════════════

{template_context}
{signature_block}
═══════════════════════════════════════════════════════════════════════════════
ABSOLUTE STRUCTURAL RULES
═══════════════════════════════════════════════════════════════════════════════

1. **PRESERVE TEMPLATE STRUCTURE EXACTLY**: Keep every \\documentclass, \\usepackage, \\newcommand, \\renewcommand, \\pagestyle, margin setting, and macro definition UNCHANGED. Only modify the content inside \\begin{{document}}...\\end{{document}}.

2. **USE ONLY MACROS DEFINED IN THE TEMPLATE**: See the AVAILABLE MACROS list above. NEVER invent new macros, rename existing ones, or use macros from a different template. Every macro call MUST supply exactly the number of mandatory arguments that macro is defined with — no more, no fewer.
   Resume macro names are NOT portable between templates. \\resumeItem, \\resumeSubheading and \\resumeProjectHeading exist ONLY in Jake's and Anubhav's templates; \\cventry, \\cvitem, \\cvevent, \\runsubsection, \\headerrow and the rest are each specific to their own template. Calling one that this template does not define is an immediate fatal "Undefined control sequence". If a rule below shows an example macro name that is not in THIS template's macro list, substitute this template's equivalent — follow the rule's intent, never its literal macro name.

3. **HEADER**: Replace the name, phone, email, linkedin, github in the header using the EXACT header pattern shown above. Keep the same structure — only change the data values.

4. **SECTIONS**: For each section, follow the template's pattern exactly as described in the AVAILABLE MACROS section.

5. **CONDITIONAL SECTIONS**:
   - Work Experience Provided = {has_experience}. If FALSE, DELETE the entire Experience/Work Experience section.
   - Education Provided = {has_education}. If FALSE, DELETE the entire Education section.
   - If user provided a Summary/Bio AND the template supports it, include a Summary section.
   - If user provided Certifications, add them in a relevant section.
   - If user provided Achievements/Honors, add them in a relevant section (use the template's Honors/Awards section if it has one; otherwise fold them into Achievements or a Certifications-and-Achievements block). Do not invent an achievement's wording — use what was provided, only rephrasing for ATS tone.

6. **HYPERLINKS**: {_hyperlink_rule(template_id)}

7. **NO EMPTY ENVIRONMENTS**: Never output a list/section environment (ListStart...ListEnd, begin...end) without items inside. Delete empty sections entirely.

7a. **BULLETS MUST LIVE INSIDE A LIST**: \\item — and every template macro that expands to one (\\resumeItem, \\resumeSubheading, \\resumeItemWithoutTitle, \\cvitem-style bullets) — is only legal inside an open list. Always wrap them in this template's list pair (\\resumeItemListStart…\\resumeItemListEnd, \\resumeSubHeadingListStart…\\resumeSubHeadingListEnd, \\begin{{itemize}}…\\end{{itemize}}, \\begin{{tightemize}}…\\end{{tightemize}}, whichever this template provides). A bullet emitted straight under a \\section with no list around it is the fatal error "Lonely \\item--perhaps a missing list environment". For a one-line Summary section, write plain text, NOT a bullet macro.

8. **NO TRAILING BACKSLASHES**: Never put \\\\ after the last item in a skills list or after a subheading call.

═══════════════════════════════════════════════════════════════════════════════
COMPLETENESS RULES — CRITICAL (READ CAREFULLY)
═══════════════════════════════════════════════════════════════════════════════

9. **FILL EVERY SECTION**: If the user provided education, experience, projects, and skills — ALL of them MUST appear in the output. Never skip or omit a section that has user data. A resume that only shows projects and skills but skips experience/education is UNACCEPTABLE.

10. **PAGE BUDGET**: {_page_budget_text(target_pages)}. If user data is sparse:
    - Expand project bullet points with more technical detail extracted from the repository README, commit messages, or file structure.
    - Add more descriptive skill categories.
    - Use 3-4 bullet points per project/experience entry instead of 1-2.
    - Each bullet should be 1-2 complete lines, not one-word fragments.

11. **BULLET POINT DENSITY**: Use 3-4 bullet points per experience/project entry. Each bullet point should describe a concrete achievement, technology used, or impact. Single-word or single-phrase bullets are NOT acceptable.

11a. **PROJECT BULLET MINIMUM (STRICT, NON-NEGOTIABLE)**: Every single project entry MUST have AT LEAST 3 separate bullet points, using whichever bullet macro THIS template provides (see AVAILABLE MACROS — it may be plain \\item, or a template-specific macro). A project with only 1 or 2 bullets is a VALIDATION FAILURE. Each bullet must be a full sentence/clause (1-2 lines), describing a distinct aspect: what the project does, a specific feature or architectural detail, and a measurable outcome/impact/scale. Never collapse a project down to a single one-line summary.
    EXCEPTION — TEMPLATE WINS: if this template's TEMPLATE NOTES say its Projects section is built from a single entry macro rather than a per-project bullet list, follow the template's pattern instead of this rule. Put the same substance (what it does, a key technical detail, the impact, the tech stack) into that entry's description text as full sentences. Never bend a macro to fit this rule — supplying the wrong number of arguments is a fatal compile error, and this rule is not worth breaking the build for.

11b. **TECH STACK ON ITS OWN LINE (REQUIRED)**: In addition to the 3+ description bullets above, every project entry MUST include ONE dedicated bullet, placed FIRST in that project's bullet list, stating the tech stack ONLY. This applies only where the template gives each project a bullet list; where the TEMPLATE NOTES specify a single-entry project macro instead, name the tech stack inside that entry (e.g. in the heading argument, or as "Tech: ..." at the end of the description) and emit no extra bullet. {_tech_stack_rule()}
    IMPORTANT: with a two-argument bullet macro, do NOT put a colon at the end of the
    label. Those macros already insert ": " between the two arguments, so a label
    written as "Tech Stack:" renders as "Tech Stack:: ..." with a doubled colon.
    Write the label without the colon. The same applies to every other labelled
    bullet (Project Overview, Objective, and so on). This tech-stack line is separate from — and in addition to — the 3+ substantive description bullets; it does not count toward the minimum of 3. So every project entry has 4+ bullets total: 1 tech-stack line + 3+ description bullets. Still also put the tech stack in the project heading (Rule 14) where the template supports it — the dedicated bullet line is required regardless.

12. **SECTION ORDER & BALANCE**: Arrange sections to fill the page naturally. Do not cluster all content at the top with empty space at the bottom. Use the RECOMMENDED SECTION ORDER from the template rules above.

13. **COMPLETE DOCUMENT — NO TRUNCATION**: Your output MUST start with \\documentclass (or % comment) and MUST end with \\end{{document}}. If your output is cut off mid-document, the resume WILL FAIL to compile. Budget your response to include the FULL document. Never stop mid-section.

14. **PROJECTS FROM REPOSITORIES**: For each selected GitHub repository, create a project entry with:
    - Project name and tech stack from the repo metadata (in the heading, per the template's project-heading macro)
    - A dedicated first bullet stating the tech stack (see Rule 11b)
    - AT LEAST 3 additional bullet points describing what the project does, key features, and technical/architectural details or impact (see Rule 11a) — 4+ bullets total per project
    - Pull details from the README excerpt, commit messages, file tree, and manifests
    - If the user provided performance notes for a repo, incorporate them into the bullets

═══════════════════════════════════════════════════════════════════════════════
ZERO HALLUCINATION
═══════════════════════════════════════════════════════════════════════════════

15. **USE ONLY PROVIDED DATA**: Do NOT invent job titles, company names, dates, metrics, or technologies the user didn't provide. You may rephrase and enhance wording for ATS optimization, but never fabricate facts.

16. **OUTPUT FORMAT**: Return ONLY raw LaTeX starting with % or \\documentclass. NO markdown code blocks (```), NO explanatory text before or after the LaTeX.

17. **NO PLACEHOLDER ECHO (CRITICAL)**: The template contains sample details (e.g. 'Jake Ryan', 'Southwestern University', 'Gitlytics', 'Simple Paintball', 'Sourabh Bajaj', 'Danny Phang', 'Zachary Deedy'). You MUST replace ALL of these with the real candidate details. If any placeholder from the original template remains in your output, it is a critical failure.

18. **DELETE PLACEHOLDER SECTIONS — NEVER FILL THEM (CRITICAL)**: Templates ship with demo sections the candidate has no data for — Languages, Interests, Hobbies, References, Publications, 'Extra 1/2/3', 'A Day of My Life', and in some templates an entire cover letter after \\clearpage. If the user data contains nothing for such a section, DELETE the section wholesale, heading and all. Do NOT keep the heading, and above all do NOT invent contents for it. Writing 'Languages: English (Fluent), Hindi (Fluent)' or 'Interests: Hiking, Reading' when the user supplied neither is a fabrication and a critical failure, and it also pushes the resume past its page target. An absent section is correct; an invented one is not."""
