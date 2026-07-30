"""
Template Registry — Maps every supported template to its compilation engine,
document class, available macros, header pattern, and section structure.

This metadata is injected into the LLM system prompt so it knows EXACTLY what
LaTeX constructs are valid for a given template and will compile correctly.

`supports_hyperlinks` records whether the template's preamble actually makes
\\href available (directly, via its .cls, or via a class option such as AltaCV's
`withhyper`). It is NOT decoration: the generated document's preamble is
replaced with the original template's before compiling, so the model cannot
rescue a missing \\usepackage{hyperref} by adding one. dphang is the only
template without it — see latex_sanitizer.strip_hyperlinks.
"""

TEMPLATE_REGISTRY = {

    # ── 1. Jake's Resume (pdflatex) ──────────────────────────────────────────
    "Jake_s_Resume__3_": {
        "display_name": "Jake's Resume",
        "engine": "pdflatex",
        "supports_hyperlinks": True,
        "document_class": "article (letterpaper, 11pt)",
        "header_pattern": (
            "\\begin{center} block with:\n"
            "  \\textbf{\\Huge\\scshape NAME} \\\\ \\vspace{1pt}\n"
            "  \\small PHONE $|$ \\href{mailto:EMAIL}{\\underline{EMAIL}} $|$\n"
            "  \\href{LINKEDIN_URL}{\\underline{linkedin.com/in/ID}} $|$\n"
            "  \\href{GITHUB_URL}{\\underline{github.com/ID}}"
        ),
        "available_macros": [
            "\\resumeSubheading{Organization}{Location}{Title/Degree}{Date Range}  — 4 required args",
            "\\resumeSubSubheading{Title}{Date Range}  — 2 args",
            "\\resumeProjectHeading{\\textbf{Project Name} $|$ \\emph{Tech Stack}}{Date Range}  — 2 args",
            "\\resumeItem{Bullet point text}  — 1 arg",
            "\\resumeSubItem{Text}  — 1 arg",
            "\\resumeSubHeadingListStart  — opens a subheading list",
            "\\resumeSubHeadingListEnd  — closes a subheading list",
            "\\resumeItemListStart  — opens a bullet list",
            "\\resumeItemListEnd  — closes a bullet list",
        ],
        "skills_pattern": (
            "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            "  \\small{\\item{\n"
            "    \\textbf{Languages}{: Python, Java, ...} \\\\\n"
            "    \\textbf{Frameworks}{: React, Node.js, ...} \\\\\n"
            "    \\textbf{Tools}{: Git, Docker, ...}\n"
            "  }}\n"
            "\\end{itemize}"
        ),
        "section_order": ["Education", "Experience", "Projects", "Technical Skills"],
        "notes": (
            "Single-file template. All macros defined in preamble via \\newcommand. "
            "Do NOT use \\fontspec, \\fontdir, or XeTeX/LuaTeX-only commands. "
            "\\section{} creates horizontal-ruled section headers."
        ),
    },

    # ── 2. AltaCV (lualatex) ─────────────────────────────────────────────────
    "AltaCV_Template__1_": {
        "display_name": "AltaCV",
        "engine": "lualatex",
        "supports_hyperlinks": True,
        "document_class": "altacv (10pt, a4paper, withhyper)",
        "header_pattern": (
            "\\name{First Last}\n"
            "\\tagline{Job Title}\n"
            "\\personalinfo{\n"
            "  \\email{email@example.com}\n"
            "  \\phone{000-000-0000}\n"
            "  \\location{City, Country}\n"
            "  \\linkedin{linkedin-id}\n"
            "  \\github{github-id}\n"
            "}"
        ),
        "available_macros": [
            "\\cvsection{Section Title}  — creates a section",
            "\\cvevent{Title}{Organization}{Date Range}{Location}  — 4 args",
            "\\cvtag{Skill}  — inline skill tag",
            "\\cvskill{Skill Name}{Rating 1-5}  — skill with rating dots",
            "\\divider  — horizontal divider between entries",
            "\\begin{itemize} ... \\item ... \\end{itemize}  — bullet lists inside cvevent",
            # Real signature is \wheelchart[inner]{outer radius}{inner radius}{data}
            # — 4 args, first optional. Documented here as DO-NOT-USE because
            # getting it wrong is a fatal compile error and it adds nothing to
            # an ATS resume.
            "\\wheelchart  — DO NOT USE (decorative pie chart, 4 args, fatal if mis-called)",
        ],
        "skills_pattern": (
            "Use \\cvtag{Python} \\cvtag{JavaScript} inline tags, OR\n"
            "\\cvskill{Python}{5} for rated skills"
        ),
        "section_order": ["Experience", "Projects", "Education", "Skills", "A Day of My Life", "Achievements"],
        "notes": (
            "Two-column layout using paracol. Left column is wider (main content), "
            "right column is for skills/education/extras. Uses altacv.cls. "
            "Requires lualatex for fontspec. Has \\switchcolumn for column switching. "
            "Uses \\cvsection{} instead of \\section{}."
        ),
    },

    # ── 3. Deedy CV (xelatex) ────────────────────────────────────────────────
    "Deedy_CV__1_": {
        "display_name": "Deedy CV",
        "engine": "xelatex",
        "supports_hyperlinks": True,
        "document_class": "deedy-resume-openfont",
        "header_pattern": (
            "\\namesection{First}{Last}{\n"
            "  \\urlstyle{same}\\href{PORTFOLIO}{portfolio} |\n"
            "  \\href{mailto:EMAIL}{EMAIL} | PHONE |\n"
            "  \\href{LINKEDIN}{LinkedIn} | \\href{GITHUB}{GitHub}\n"
            "}"
        ),
        "available_macros": [
            "\\section{Section Title}  — creates a section header",
            "\\subsection{Subsection Title}  — subsection",
            "\\runsubsection{Organization/Project}  — bold entry name",
            "\\descript{| Role/Description}  — role description after runsubsection",
            "\\location{Date Range | Location}  — date and location line",
            "\\sectionsep  — spacing between sections",
            "\\begin{tightemize} \\item ... \\end{tightemize}  — tight bullet list",
        ],
        "skills_pattern": (
            "\\section{Skills}\n"
            "\\subsection{Programming}\n"
            "Python \\textbullet{} Java \\textbullet{} JavaScript \\\\\n"
            "\\subsection{Frameworks}\n"
            "React \\textbullet{} Node.js"
        ),
        "section_order": ["Education", "Experience", "Research", "Projects", "Skills", "Awards"],
        "notes": (
            "Two-column layout using minipage. Left column (narrow) for education/skills, "
            "right column (wide) for experience/projects. Uses custom .cls with custom fonts. "
            "MUST compile with xelatex. Uses \\begin{minipage} for column layout."
        ),
    },

    # ── 4. ModernCV (pdflatex) ───────────────────────────────────────────────
    "ModernCV_and_Cover_Letter_Template__2_": {
        "display_name": "ModernCV",
        "engine": "pdflatex",
        "supports_hyperlinks": True,
        "document_class": "moderncv (11pt, a4paper, sans)",
        "header_pattern": (
            "\\name{First}{Last}\n"
            "\\title{Resume Title}\n"
            "\\address{Street}{City}{Country}\n"
            "\\phone[mobile]{+1~(234)~567~890}\n"
            "\\email{email@example.com}\n"
            "\\homepage{www.example.com}\n"
            "\\social[linkedin]{linkedin-id}\n"
            "\\social[github]{github-id}"
        ),
        "available_macros": [
            "\\section{Section Title}  — section header",
            "\\cventry{Dates}{Title}{Organization}{Location}{Grade/GPA}{Description}  — 6 args",
            "\\cvitem{Label}{Description}  — key-value item",
            "\\cvitemwithcomment{Label}{Description}{Comment}  — item with right-aligned comment",
            "\\cvlistitem{Text}  — single bullet list item",
            "\\cvlistdoubleitem{Left Text}{Right Text}  — two-column list item",
            "\\moderncvstyle{classic}  — style: casual, classic, banking, oldstyle, fancy",
            "\\moderncvcolor{blue}  — color: black, blue, burgundy, green, grey, orange, purple, red",
        ],
        "skills_pattern": (
            "\\section{Computer Skills}\n"
            "\\cvitem{Languages}{Python, Java, JavaScript}\n"
            "\\cvitem{Frameworks}{React, Node.js, Django}"
        ),
        "section_order": ["Education", "Experience", "Skills", "Languages", "Interests"],
        "notes": (
            "Single-file template with moderncv class. Style and color set via preamble. "
            "Compiles with pdflatex. Do NOT use fontspec. "
            "PLACEHOLDER SECTIONS — DELETE THEM: this template ships with fully "
            "populated demo sections (Languages, Interests, Extra 1/2/3, a "
            "\\subsection{Vocational} heading) and a whole cover letter after "
            "\\clearpage (\\recipient, \\opening, \\makelettertitle, \\closing, "
            "\\enclosure). None of that is the candidate's data. Delete every one "
            "of those sections and the entire cover letter outright — do NOT "
            "invent languages, hobbies or interests to fill them. Keeping them "
            "both fabricates facts and pushes the CV onto a second page."
        ),
    },

    # ── 5. Resume Template by Anubhav (pdflatex) ────────────────────────────
    "Resume_Template_by_Anubhav__2_": {
        "display_name": "Anubhav Resume",
        "engine": "pdflatex",
        "supports_hyperlinks": True,
        "document_class": "article (a4paper, 20pt)",
        "header_pattern": (
            "\\begin{center}\n"
            "  {\\LARGE \\scshape NAME} \\\\ \\vspace{1pt}\n"
            "  \\small PHONE ~ \\textbar ~ EMAIL ~ \\textbar ~\n"
            "  \\href{LINKEDIN}{LinkedIn} ~ \\textbar ~ \\href{GITHUB}{GitHub}\n"
            "\\end{center}"
        ),
        "available_macros": [
            "\\resumeSubheading{Organization}{Location}{Title}{Dates}  — 4 args, ALL MANDATORY (Education and Experience entries only)",
            "\\resumeSubItem{Project Name (Tech Stack)}{Description}  — 2 args, THIS IS THE PROJECTS MACRO",
            "\\resumeItem{Label}{Description}  — 2 args, BOTH MANDATORY (bold label, then text)",
            "\\resumeSubHeadingListStart / \\resumeSubHeadingListEnd  — list wrappers",
            "\\resumeItemListStart / \\resumeItemListEnd  — item list wrappers",
            # Defined in the template but never used by it, and its body is
            # `\item\small{ {\vspace{-2pt}} }` — argument #1 is DISCARDED, so
            # any text passed to it silently vanishes. It also expands to
            # \item, so calling it outside a list gives "Lonely \item".
            "\\resumeItemWithoutTitle  — DO NOT USE (throws its argument away; also fatal outside a list)",
        ],
        "skills_pattern": (
            "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            "  \\small{\\item{\n"
            "    \\textbf{Languages}{: Python, Java} \\\\\n"
            "    \\textbf{Technologies}{: React, Docker}\n"
            "  }}\n"
            "\\end{itemize}"
        ),
        "section_order": ["Education", "Experience", "Projects", "Technical Skills", "Achievements"],
        "notes": (
            "Very similar to Jake's Resume but the macros differ in ARITY — this is "
            "the single most common source of fatal compile errors with this template. "
            "\\resumeItem takes TWO MANDATORY arguments: \\resumeItem{Label}{Description}. "
            "It is NOT \\resumeItem[Label]{Description} and NOT a single-argument macro "
            "like Jake's. \\resumeSubItem likewise takes 2. Omitting the second argument "
            "makes TeX swallow the following tokens and fail with "
            "'Missing number, treated as zero'. Single-file, pdflatex only. "
            "PROJECTS: this template has NO project-heading macro — there is no "
            "\\resumeProjectHeading here (that is Jake's). Each project is ONE "
            "\\resumeSubItem{Project Name (Tech Stack)}{What it does, key detail, impact. "
            "Tech: ...} inside \\resumeSubHeadingListStart/End, exactly as the sample "
            "does. Do NOT use \\resumeSubheading for a project: it needs FOUR arguments "
            "and calling it with two is a fatal compile error."
        ),
    },

    # ── 6. dphang CV Template (pdflatex) ─────────────────────────────────────
    "dphang_CV_Template__1_": {
        "display_name": "dphang CV",
        "engine": "pdflatex",
        # The ONLY template whose preamble never loads hyperref — no
        # \usepackage{hyperref}, no class that pulls it in. \href here is a
        # fatal "Undefined control sequence", and adding the package is not an
        # option because the preamble is restored from the original template
        # before compiling.
        "supports_hyperlinks": False,
        "document_class": "article (11pt, letterpaper)",
        "header_pattern": (
            "\\begin{center}\n"
            "  {\\LARGE \\textbf{NAME}} \\\\\n"
            "  Location \\\\\n"
            "  PHONE ~ \\textbar ~ EMAIL ~ \\textbar ~\n"
            "  linkedin.com/in/ID ~ \\textbar ~ github.com/ID\n"
            "\\end{center}"
        ),
        "available_macros": [
            "\\headerrow{Left Text}{Right Text}  — two-column row (tabular*)",
            "\\begin{itemize} \\item ... \\end{itemize}  — standard bullet list",
            "\\CPP  — pretty-prints C++",
            "\\begin{indentsection}{indent}  — indented section",
            "\\begin{unindentsection}{indent}  — un-indented section",
        ],
        "skills_pattern": (
            "\\headerrow{\\textbf{Languages}}{}\n"
            "\\begin{indentsection}{\\parindent}\n"
            "  Python, Java, JavaScript, C/\\CPP\n"
            "\\end{indentsection}"
        ),
        "section_order": ["Skills", "Experience", "Education", "Projects"],
        "notes": (
            "Simple article-based template with \\headerrow for entries. "
            "Uses fontawesome5 for icons. Uses standard \\begin{itemize} for bullets. "
            "No custom resume macros — uses plain LaTeX with \\headerrow. "
            "Compiles with pdflatex. "
            "NO HYPERREF: this preamble does not load hyperref, so \\href and "
            "\\url are UNDEFINED and fatal. Write every link as plain text "
            "(github.com/ID, linkedin.com/in/ID, the email address itself)."
        ),
    },
}


def get_template_metadata(template_id: str) -> dict:
    """Get full metadata for a template. Returns None if not found."""
    return TEMPLATE_REGISTRY.get(template_id)


def get_template_context(template_id: str) -> str:
    """
    Build a formatted string describing this template's rules for the system prompt.
    The LLM reads this to know exactly which macros/patterns to use.
    """
    meta = TEMPLATE_REGISTRY.get(template_id)
    if not meta:
        return f"WARNING: Unknown template '{template_id}'. Preserve the template structure as-is."

    macros_list = "\n".join(f"   - {m}" for m in meta["available_macros"])
    section_order = " → ".join(meta["section_order"])

    return f"""TEMPLATE: {meta['display_name']} (ID: {template_id})
COMPILER: {meta['engine']} — You MUST only use LaTeX features compatible with {meta['engine']}.
DOCUMENT CLASS: {meta['document_class']}

HEADER PATTERN (replace data but keep the structure):
{meta['header_pattern']}

AVAILABLE MACROS (use ONLY these — NEVER invent new ones):
{macros_list}

SKILLS PATTERN:
{meta['skills_pattern']}

RECOMMENDED SECTION ORDER: {section_order}

TEMPLATE NOTES:
{meta['notes']}"""


def list_templates_summary() -> list:
    """Return a list of template summaries for the /api/templates endpoint."""
    return [
        {
            "id": tid,
            "display_name": meta["display_name"],
            "engine": meta["engine"],
            "document_class": meta["document_class"],
            "section_order": meta["section_order"],
        }
        for tid, meta in TEMPLATE_REGISTRY.items()
    ]
