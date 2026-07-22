"""
Template Registry — Maps every supported template to its compilation engine,
document class, available macros, header pattern, and section structure.

This metadata is injected into the LLM system prompt so it knows EXACTLY what
LaTeX constructs are valid for a given template and will compile correctly.
"""

TEMPLATE_REGISTRY = {

    # ── 1. Jake's Resume (pdflatex) ──────────────────────────────────────────
    "Jake_s_Resume__3_": {
        "display_name": "Jake's Resume",
        "engine": "pdflatex",
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
            "\\wheelchart{...}  — pie chart for skills (optional)",
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

    # ── 4. Awesome CV (xelatex) ──────────────────────────────────────────────
    "Awesome_CV__3_": {
        "display_name": "Awesome CV",
        "engine": "xelatex",
        "document_class": "awesome-cv (11pt, a4paper)",
        "header_pattern": (
            "\\name{First}{Last}\n"
            "\\position{Job Title{\\enskip\\cdotp\\enskip}Specialization}\n"
            "\\address{Full Address}\n"
            "\\mobile{(+XX) XX-XXXX-XXXX}\n"
            "\\email{email@example.com}\n"
            "\\homepage{www.example.com}\n"
            "\\github{github-id}\n"
            "\\linkedin{linkedin-id}\n"
            "\\quote{\"Motivational quote\"}"
        ),
        "available_macros": [
            "\\cvsection{Section Title}  — section header",
            "\\cventry{Title}{Organization}{Location}{Date Range}{Description/Bullets}  — 5 args",
            "\\cvsubentry{Title}{Date Range}{Description}{Details}  — 4 args",
            "\\begin{cvitems} \\item{Text} \\end{cvitems}  — bullet list inside cventry",
            "\\begin{cventries} ... \\end{cventries}  — wraps multiple cventry",
            "\\begin{cvhonors} \\cvhonor{Award}{Org}{Location}{Date} \\end{cvhonors}  — honors/awards",
            "\\makecvheader[C]  — prints the header (C=center, L=left, R=right)",
            "\\makecvfooter{\\today}{Name~~~·~~~Résumé}{\\thepage}  — footer",
        ],
        "skills_pattern": (
            "Use \\cvsection{Skills} with \\begin{cvitems} containing \\item{} entries, OR\n"
            "plain text with categories."
        ),
        "section_order": ["Summary", "Experience", "Honors", "Projects", "Education", "Skills"],
        "notes": (
            "Multi-file template with \\input{resume/section.tex} for each section. "
            "The concatenated output from CV_BUILDER inlines all \\input{} files. "
            "Uses awesome-cv.cls with custom fonts in fonts/ directory. "
            "\\fontdir[fonts/] sets the font path. MUST compile with xelatex. "
            "Header is set via preamble commands, NOT inside \\begin{document}."
        ),
    },

    # ── 5. PlushCV (xelatex) ─────────────────────────────────────────────────
    "PlushCV__2_": {
        "display_name": "PlushCV",
        "engine": "xelatex",
        "document_class": "plushcv",
        "header_pattern": (
            "\\namesection{First}{Last}{Job Title}{\n"
            "  \\contactline\n"
            "    {\\href{URL}{homepage}}\n"
            "    {\\href{GITHUB_URL}{github-id}}\n"
            "    {\\href{LINKEDIN_URL}{linkedin-id}}\n"
            "    {\\href{mailto:EMAIL}{EMAIL}}\n"
            "    {\\href{tel:PHONE}{PHONE}}\n"
            "}"
        ),
        "available_macros": [
            "\\section{Section Title}  — section header",
            "\\runsubsection{Organization/Project}  — bold entry name",
            "\\descript{| Role/Description}  — role description",
            "\\location{Date Range | Location}  — date/location line",
            "\\sectionsep  — spacing between sections",
            "\\begin{tightemize} \\item ... \\end{tightemize}  — tight bullet list",
            "\\skills{\\skillEntry{Category}{skill1, skill2, ...}}  — skills block",
        ],
        "skills_pattern": (
            "\\section{Skills}\n"
            "\\begin{tabular}{rl}\n"
            "  \\textsc{Languages}: & Python, Java \\\\\n"
            "  \\textsc{Frameworks}: & React, Node.js\n"
            "\\end{tabular}"
        ),
        "section_order": ["Education", "Experience", "Projects", "Skills"],
        "notes": (
            "Two-column layout similar to Deedy but with different styling. "
            "Uses PlushCV.cls with custom fonts and icons. "
            "MUST compile with xelatex. Uses minipage for columns."
        ),
    },

    # ── 6. ModernCV (pdflatex) ───────────────────────────────────────────────
    "ModernCV_and_Cover_Letter_Template__2_": {
        "display_name": "ModernCV",
        "engine": "pdflatex",
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
            "Also includes a cover letter section (\\recipient, \\opening, \\closing). "
            "Compiles with pdflatex. Do NOT use fontspec."
        ),
    },

    # ── 7. Resume Template by Anubhav (pdflatex) ────────────────────────────
    "Resume_Template_by_Anubhav__2_": {
        "display_name": "Anubhav Resume",
        "engine": "pdflatex",
        "document_class": "article (a4paper, 20pt)",
        "header_pattern": (
            "\\begin{center}\n"
            "  {\\LARGE \\scshape NAME} \\\\ \\vspace{1pt}\n"
            "  \\small PHONE ~ \\textbar ~ EMAIL ~ \\textbar ~\n"
            "  \\href{LINKEDIN}{LinkedIn} ~ \\textbar ~ \\href{GITHUB}{GitHub}\n"
            "\\end{center}"
        ),
        "available_macros": [
            "\\resumeSubheading{Organization}{Location}{Title}{Dates}  — 4 args",
            "\\resumeItem[Label]{Description}  — bullet with optional bold label",
            "\\resumeSubHeadingListStart / \\resumeSubHeadingListEnd  — list wrappers",
            "\\resumeItemListStart / \\resumeItemListEnd  — item list wrappers",
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
            "Very similar to Jake's Resume but with slightly different macros. "
            "\\resumeItem takes an optional label arg: \\resumeItem[Label]{Description}. "
            "Single-file, pdflatex only."
        ),
    },

    # ── 8. dphang CV Template (pdflatex) ─────────────────────────────────────
    "dphang_CV_Template__1_": {
        "display_name": "dphang CV",
        "engine": "pdflatex",
        "document_class": "article (11pt, letterpaper)",
        "header_pattern": (
            "\\begin{center}\n"
            "  {\\LARGE \\textbf{NAME}} \\\\\n"
            "  Location \\\\\n"
            "  PHONE ~ \\textbar ~ \\href{mailto:EMAIL}{EMAIL} ~ \\textbar ~\n"
            "  \\href{LINKEDIN}{LinkedIn} ~ \\textbar ~ \\href{GITHUB}{GitHub}\n"
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
            "Compiles with pdflatex."
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
