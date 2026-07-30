"""
Macro arity validator — catch wrong-argument-count macro calls BEFORE compiling.

Motivating failure (2026-07-29): the Anubhav template defines

    \\newcommand{\\resumeItem}[2]{ \\item\\small{ \\textbf{#1}{: #2 \\vspace{-2pt}} } }

i.e. TWO mandatory arguments, but the prompt registry described it as
`\\resumeItem[Label]{Description}`. The LLM dutifully emitted one-argument
calls, TeX scanned forward for the missing argument, and the compile died with
"Missing number, treated as zero" — an error message that points at the symptom
and says nothing about the real cause.

Rather than trust hand-written registry documentation (which drifts from the
templates), arity is parsed from the template source at runtime. The template
IS the ground truth.
"""

import re
from typing import Dict, List, Optional, Tuple

# \newcommand{\foo}[2][default]{...} / \renewcommand*\foo[1]{...}
_DEF_PATTERN = re.compile(
    r"\\(?:re)?newcommand\*?\s*"
    r"(?:\{\s*\\([A-Za-z@]+)\s*\}|\\([A-Za-z@]+))"
    r"\s*(?:\[(\d+)\])?"
    r"\s*(\[[^\]]*\])?"
)

# Macros we never police: LaTeX built-ins and kernel commands whose arity is
# context-dependent or provided by a document class we can't see.
_IGNORED = {
    "begin", "end", "item", "documentclass", "usepackage", "newcommand",
    "renewcommand", "providecommand", "def", "section", "subsection",
    "subsubsection", "textbf", "textit", "emph", "small", "large", "href",
    "underline", "vspace", "hspace", "text", "input", "include",
}


def extract_macro_arity(template_tex: str) -> Dict[str, Tuple[int, bool]]:
    """
    Map macro name -> (total args, first arg is optional) from \\newcommand
    definitions in the template source.

    With `[n][default]`, LaTeX makes the FIRST of the n arguments optional, so
    the number of mandatory braces is n-1.
    """
    arity: Dict[str, Tuple[int, bool]] = {}
    for m in _DEF_PATTERN.finditer(template_tex):
        name = m.group(1) or m.group(2)
        if not name or name in _IGNORED:
            continue
        nargs = int(m.group(3) or 0)
        has_optional = bool(m.group(4))
        arity[name] = (nargs, has_optional)
    return arity


def mandatory_args(nargs: int, has_optional: bool) -> int:
    """How many brace groups a call must supply."""
    return max(0, nargs - 1) if has_optional else nargs


# ── Undefined-macro detection ────────────────────────────────────────────────
#
# Motivating failure (2026-07-30): the system prompt's tech-stack rule spelled
# its example with \resumeItem, a macro that exists ONLY in Jake's and Anubhav's
# templates. Generating with AltaCV or PlushCV produced
#
#     \item \resumeItem{Tech Stack}{Python, FastAPI, LaTeX}
#     ./doc.tex:147: Undefined control sequence.
#
# The arity gate could not see it: it only polices macros the template DEFINES,
# and an undefined macro has no arity to check. Same class of bug as the arity
# one — documentation drifting from the template — so it gets the same
# treatment: derive ground truth from the template at request time.

# Additional definition forms beyond \newcommand/\renewcommand.
_EXTRA_DEF_PATTERNS = [
    re.compile(r"\\(?:e|g|x)?def\s*\\([A-Za-z@]+)"),
    re.compile(r"\\DeclareRobustCommand\*?\s*(?:\{\s*\\([A-Za-z@]+)\s*\}|\\([A-Za-z@]+))"),
    re.compile(r"\\(?:New|Renew|Provide|Declare)DocumentCommand\s*(?:\{\s*\\([A-Za-z@]+)\s*\}|\\([A-Za-z@]+))"),
    re.compile(r"\\newenvironment\*?\s*\{\s*([A-Za-z@*]+)\s*\}"),
    re.compile(r"\\(?:let|newlength|newcount|newdimen|newskip|newtoks|newbox)\s*\\([A-Za-z@]+)"),
    re.compile(r"\\newif\s*\\if([A-Za-z@]+)"),
    re.compile(r"\\newcolumntype\s*\{\s*([A-Za-z@]+)\s*\}"),
    re.compile(r"\\(?:newfontfamily|newfontface)\s*\\([A-Za-z@]+)"),
]

# LaTeX kernel and near-universal package commands. A template's own source is
# the primary allow-list; this covers commands an LLM may legitimately reach for
# that the sample document happens never to use. Erring generous here is
# deliberate — a false positive triggers a pointless repair round-trip, while a
# missed exotic macro still gets caught by the compile.
_KERNEL_MACROS = {
    # structure
    "documentclass", "usepackage", "begin", "end", "item", "input", "include",
    "section", "subsection", "subsubsection", "paragraph", "chapter", "part",
    "newcommand", "renewcommand", "providecommand", "def", "newenvironment",
    "renewenvironment", "DeclareRobustCommand", "let", "relax", "expandafter",
    "makeatletter", "makeatother", "csname", "endcsname", "protect",
    # text formatting
    "textbf", "textit", "texttt", "textsc", "textrm", "textsf", "textmd",
    "textnormal", "textsuperscript", "textsubscript", "underline", "emph",
    "bf", "it", "sc", "rm", "sf", "tt", "sl", "em", "normalfont", "bfseries",
    "itshape", "scshape", "rmfamily", "sffamily", "ttfamily", "mdseries",
    "upshape", "slshape", "normalsize", "small", "footnotesize", "scriptsize",
    "tiny", "large", "Large", "LARGE", "huge", "Huge", "selectfont",
    # spacing and boxes
    "vspace", "hspace", "hfill", "vfill", "hrule", "vrule", "rule", "quad",
    "qquad", "smallskip", "medskip", "bigskip", "newline", "linebreak",
    "pagebreak", "newpage", "clearpage", "cleardoublepage", "noindent",
    "indent", "par", "raisebox", "makebox", "mbox", "fbox", "parbox",
    "centering", "raggedright", "raggedleft", "baselineskip", "linewidth",
    "textwidth", "textheight", "columnwidth", "height", "width", "depth",
    "phantom", "hphantom", "vphantom", "strut", "nolinebreak", "allowbreak",
    "setlength", "addtolength", "arraystretch", "tabcolsep", "parindent",
    "parskip", "leftmargin", "topsep", "itemsep", "parsep", "labelsep",
    # symbols and misc
    "LaTeX", "TeX", "today", "thepage", "textbullet", "textbar", "textbackslash",
    "textendash", "textemdash", "textasciitilde", "textasciicircum",
    "textdegree", "textperiodcentered", "ldots", "dots", "cdot", "cdotp",
    "bullet", "star", "dag", "ddag", "S", "P", "copyright", "pounds", "euro",
    "&", "%", "$", "#", "_", "{", "}", "~", "^", "\\",
    "enskip", "thinspace", "negthinspace", "space", "nobreakspace",
    "url", "href", "hyperlink", "hypertarget", "urlstyle", "nolinkurl",
    "color", "textcolor", "colorlet", "definecolor", "pagecolor", "colorbox",
    "includegraphics", "caption", "label", "ref", "pageref", "cite",
    "footnote", "footnotemark", "footnotetext", "marginpar",
    "pagestyle", "thispagestyle", "geometry", "setmainfont", "setsansfont",
    "multicolumn", "multirow", "cline", "hline", "toprule", "midrule",
    "bottomrule", "extracolsep", "arrayrulewidth",
    "ifthenelse", "ifdefined", "ifx", "else", "fi", "newif", "setbool",
    "the", "value", "arabic", "roman", "alph", "stepcounter", "setcounter",
    "newcounter", "addtocounter", "refstepcounter",
}


def _registry_macro_names(template_id: Optional[str]) -> set:
    """
    Macro names the template registry documents for this template.

    The registry lists macros that a template's .cls provides but its sample
    document may never use. CV_BUILDER's template endpoints only return .tex
    files, so the .cls is not visible here — the registry is the only record of
    those, and leaving them out would flag valid usage.
    """
    if not template_id:
        return set()
    try:
        from app.prompts.template_registry import get_template_metadata
    except Exception:
        return set()

    meta = get_template_metadata(template_id)
    if not meta:
        return set()

    names = set()
    for entry in meta.get("available_macros", []):
        names.update(re.findall(r"\\([A-Za-z@]+)", entry))
    for key in ("header_pattern", "skills_pattern"):
        names.update(re.findall(r"\\([A-Za-z@]+)", meta.get(key, "")))
    return names


def collect_defined_macros(template_tex: str, template_id: Optional[str] = None) -> set:
    """
    Every control sequence that is known to resolve for this template.

    Three sources, in order of authority:
      1. macros the template DEFINES (\\newcommand, \\def, \\newenvironment, …)
      2. macros the template USES — the sample compiles, so whatever it calls is
         provided by its class or one of its packages. This is what covers
         class-provided macros like AltaCV's \\cvevent or Deedy's \\runsubsection
         without needing to read the .cls.
      3. the registry's documented macro list, for class macros the sample
         happens not to exercise.
    Plus the LaTeX kernel set.
    """
    known = set(_KERNEL_MACROS)
    known |= set(extract_macro_arity(template_tex))

    for pattern in _EXTRA_DEF_PATTERNS:
        for m in pattern.finditer(template_tex):
            name = next((g for g in m.groups() if g), None)
            if name:
                known.add(name.rstrip("*"))

    # Every control sequence the template itself invokes.
    known.update(re.findall(r"\\([A-Za-z@]+)", template_tex))

    known |= _registry_macro_names(template_id)
    return known


def check_undefined_macros(
    generated_tex: str,
    known_macros: set,
) -> List[dict]:
    """
    Find calls to control sequences this template does not provide.

    Skips definition sites (a \\newcommand introducing a name is not a call to
    it), commented lines, and anything inside verbatim-ish escapes.

    Returns a list of {macro, line, snippet, severity}.
    """
    problems: List[dict] = []
    if not known_macros:
        return problems

    def_spans = [(m.start(), m.end()) for m in _DEF_PATTERN.finditer(generated_tex)]
    for pattern in _EXTRA_DEF_PATTERNS:
        def_spans.extend((m.start(), m.end()) for m in pattern.finditer(generated_tex))

    def in_definition(idx: int) -> bool:
        return any(s <= idx < e for s, e in def_spans)

    seen = set()
    for m in re.finditer(r"\\([A-Za-z@]+)", generated_tex):
        name = m.group(1)
        if name in known_macros or name in seen or in_definition(m.start()):
            continue

        line_start = generated_tex.rfind("\n", 0, m.start()) + 1
        prefix = generated_tex[line_start : m.start()]
        if re.search(r"(?<!\\)%", prefix):
            continue
        # \\ before the name means it is an escaped backslash, not a call.
        if prefix.endswith("\\"):
            continue

        seen.add(name)
        line_end = generated_tex.find("\n", m.start())
        snippet = generated_tex[line_start : line_end if line_end > 0 else len(generated_tex)]
        line_no = generated_tex.count("\n", 0, m.start()) + 1
        problems.append(
            {
                "macro": name,
                "line": line_no,
                "snippet": snippet.strip()[:160],
                "severity": "fatal",
            }
        )
    return problems


# ── Lonely \item detection ───────────────────────────────────────────────────
#
# Motivating failure (2026-07-30): Anubhav defines
#
#     \newcommand{\resumeItemWithoutTitle}[1]{ \item\small{ {\vspace{-2pt}} } }
#
# which expands to \item. Called under \section{Summary} with no surrounding
# list, it produced
#
#     ./doc.tex:98: LaTeX Error: Lonely \item--perhaps a missing list environment.
#
# The macro IS defined, so the undefined gate can't see it, and its argument
# count IS right, so the arity gate can't either. What is wrong is the context.

_LIST_ENVIRONMENTS = {
    "itemize", "enumerate", "description", "list", "tightemize",
    "cvitems", "cventries", "cvhonors", "cvsubentries", "highlights",
}

_BEGIN_LIST_RE = re.compile(r"\\begin\s*\{\s*([A-Za-z@*]+)\s*\}")
_END_LIST_RE = re.compile(r"\\end\s*\{\s*([A-Za-z@*]+)\s*\}")


def classify_list_macros(template_tex: str) -> Tuple[set, set, set]:
    """
    Split the template's macros into (openers, closers, item_emitters).

    Derived from each macro's DEFINITION BODY:
      - a body containing \\begin{itemize} (and no \\item of its own) opens a list
      - a body containing \\end{itemize} closes one
      - a body containing a bare \\item emits a list item and therefore may only
        be called inside a list
    """
    openers, closers, emitters = set(), set(), set()

    for m in _DEF_PATTERN.finditer(template_tex):
        name = m.group(1) or m.group(2)
        if not name:
            continue
        body_start = template_tex.find("{", m.end() - 1 if m.group(4) else m.end())
        if body_start < 0:
            continue
        body_end = _match_group(template_tex, body_start, "{", "}")
        if body_end is None:
            continue
        body = template_tex[body_start:body_end]

        opens = [e for e in _BEGIN_LIST_RE.findall(body) if e.rstrip("*") in _LIST_ENVIRONMENTS]
        ends = [e for e in _END_LIST_RE.findall(body) if e.rstrip("*") in _LIST_ENVIRONMENTS]
        # \item inside the body, not counting \begin/\end lines' own text.
        has_item = re.search(r"\\item\b", body) is not None

        if opens and not ends:
            openers.add(name)
        elif ends and not opens:
            closers.add(name)
        elif has_item and not opens and not ends:
            emitters.add(name)

    return openers, closers, emitters


def check_lonely_items(generated_tex: str, template_tex: str) -> List[dict]:
    """
    Find \\item (or a macro that expands to one) used outside any list.

    Walks the body keeping a list-nesting depth, opened by \\begin{itemize} and
    friends or by a template macro whose body opens one (\\resumeItemListStart,
    \\resumeSubHeadingListStart, …), and closed by their counterparts. Anything
    emitting an item at depth 0 is a fatal "Lonely \\item".

    Returns a list of {macro, line, detail, snippet, severity}.
    """
    problems: List[dict] = []
    openers, closers, emitters = classify_list_macros(template_tex)

    start = generated_tex.find(r"\begin{document}")
    if start < 0:
        return problems

    depth = 0
    for m in re.finditer(r"\\([A-Za-z@]+)", generated_tex[start:]):
        name = m.group(1)
        idx = start + m.start()

        line_start = generated_tex.rfind("\n", 0, idx) + 1
        if re.search(r"(?<!\\)%", generated_tex[line_start:idx]):
            continue

        if name in ("begin", "end"):
            env_m = (_BEGIN_LIST_RE if name == "begin" else _END_LIST_RE).match(
                generated_tex, idx
            )
            if env_m and env_m.group(1).rstrip("*") in _LIST_ENVIRONMENTS:
                depth += 1 if name == "begin" else -1
                depth = max(0, depth)
            continue

        if name in openers:
            depth += 1
            continue
        if name in closers:
            depth = max(0, depth - 1)
            continue

        if depth == 0 and (name == "item" or name in emitters):
            line_end = generated_tex.find("\n", idx)
            problems.append({
                "macro": name,
                "line": generated_tex.count("\n", 0, idx) + 1,
                "detail": (
                    rf"\{name} emits a list item but is not inside any list "
                    "environment (fatal: \"Lonely \\item\")"
                ),
                "snippet": generated_tex[
                    line_start : line_end if line_end > 0 else len(generated_tex)
                ].strip()[:160],
                "severity": "fatal",
            })

    return problems


def format_undefined_problems(problems: List[dict]) -> str:
    return "\n".join(
        f"  - line {p['line']}: \\{p['macro']} is NOT defined by this template "
        f"→ {p['snippet']}"
        for p in problems
    )


def _skip_ws_and_comments(text: str, i: int) -> int:
    """Advance past whitespace and full-line comments between arguments."""
    while i < len(text):
        if text[i] in " \t\r\n":
            i += 1
        elif text[i] == "%":
            nl = text.find("\n", i)
            if nl == -1:
                return len(text)
            i = nl + 1
        else:
            break
    return i


def _match_group(text: str, i: int, open_ch: str, close_ch: str) -> Optional[int]:
    """
    If text[i] opens a group, return the index just past its matching close.
    Handles nesting and backslash-escaped braces. Returns None otherwise.
    """
    if i >= len(text) or text[i] != open_ch:
        return None
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2  # skip escaped char, e.g. \{ \} \\
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None  # unbalanced


def count_supplied_args(text: str, pos: int, max_args: int) -> Tuple[int, bool]:
    """
    From just after a macro name, count consecutive {...} groups supplied.
    Returns (count, saw_optional_bracket). Stops at max_args.
    """
    i = pos
    saw_optional = False

    j = _skip_ws_and_comments(text, i)
    end = _match_group(text, j, "[", "]")
    if end is not None:
        saw_optional = True
        i = end

    count = 0
    while count < max_args:
        j = _skip_ws_and_comments(text, i)
        end = _match_group(text, j, "{", "}")
        if end is None:
            break
        count += 1
        i = end
    return count, saw_optional


def check_macro_calls(
    generated_tex: str,
    arity: Dict[str, Tuple[int, bool]],
) -> List[dict]:
    """
    Find macro calls that supply the wrong number of mandatory arguments.

    Only checks macros the template actually defines. Definition sites are
    skipped, as are calls inside comments.

    Returns a list of {macro, line, expected, found, snippet, severity}.
    """
    problems: List[dict] = []
    if not arity:
        return problems

    # Where the definitions live, so we don't flag \newcommand{\foo}[2]{...}.
    def_spans = [(m.start(), m.end()) for m in _DEF_PATTERN.finditer(generated_tex)]

    def in_definition(idx: int) -> bool:
        return any(s <= idx < e for s, e in def_spans)

    for m in re.finditer(r"\\([A-Za-z@]+)", generated_tex):
        name = m.group(1)
        if name not in arity or name in _IGNORED:
            continue
        if in_definition(m.start()):
            continue

        # Skip calls sitting inside a comment.
        line_start = generated_tex.rfind("\n", 0, m.start()) + 1
        prefix = generated_tex[line_start : m.start()]
        if re.search(r"(?<!\\)%", prefix):
            continue

        nargs, has_opt = arity[name]
        need = mandatory_args(nargs, has_opt)
        if need == 0:
            continue

        found, _ = count_supplied_args(generated_tex, m.end(), need)
        if found < need:
            line_no = generated_tex.count("\n", 0, m.start()) + 1
            line_end = generated_tex.find("\n", m.start())
            snippet = generated_tex[line_start : line_end if line_end > 0 else len(generated_tex)]
            problems.append(
                {
                    "macro": name,
                    "line": line_no,
                    "expected": need,
                    "found": found,
                    "snippet": snippet.strip()[:160],
                    "severity": "fatal",
                }
            )
    return problems


def check_structural_balance(tex: str) -> List[dict]:
    """
    Detect unbalanced braces and mismatched environments in the document body.

    TeX reports these late and unhelpfully: an unclosed brace in a bullet on
    line 120 surfaces as "Missing } inserted" at the \\resumeSubHeadingListEnd
    on line 159, pointing nowhere near the actual mistake. Catching it here
    means the offending line can be named precisely.

    Ignores escaped braces, comments and verbatim-ish content.
    Returns a list of {kind, line, detail, severity}.
    """
    problems: List[dict] = []

    start = tex.find(r"\begin{document}")
    if start < 0:
        return problems

    depth = 0
    line_no = tex.count("\n", 0, start) + 1
    open_lines: List[int] = []
    env_stack: List[Tuple[str, int]] = []
    i = start

    while i < len(tex):
        c = tex[i]
        if c == "\n":
            line_no += 1
            i += 1
            continue
        if c == "\\":
            m = re.match(r"\\(begin|end)\s*\{([^{}]*)\}", tex[i:])
            if m:
                kind, env = m.group(1), m.group(2).strip()
                if kind == "begin":
                    env_stack.append((env, line_no))
                else:
                    if not env_stack:
                        problems.append({
                            "kind": "environment",
                            "line": line_no,
                            "detail": rf"\end{{{env}}} with no matching \begin",
                            "severity": "fatal",
                        })
                    elif env_stack[-1][0] != env:
                        opened, oline = env_stack.pop()
                        problems.append({
                            "kind": "environment",
                            "line": line_no,
                            "detail": (
                                rf"\end{{{env}}} closes \begin{{{opened}}} "
                                f"opened on line {oline}"
                            ),
                            "severity": "fatal",
                        })
                    else:
                        env_stack.pop()
                i += m.end()
                continue
            i += 2  # escaped char such as \{ \} \\ \&
            continue
        if c == "%":
            nl = tex.find("\n", i)
            if nl < 0:
                break
            i = nl  # newline handled next iteration
            continue
        if c == "{":
            depth += 1
            open_lines.append(line_no)
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth < 0:
                problems.append({
                    "kind": "brace",
                    "line": line_no,
                    "detail": "closing brace } with no matching {",
                    "severity": "fatal",
                })
                depth = 0
            elif open_lines:
                open_lines.pop()
            i += 1
            continue
        i += 1

    if depth > 0:
        first = open_lines[0] if open_lines else "?"
        problems.append({
            "kind": "brace",
            "line": first,
            "detail": (
                f"{depth} unclosed brace(s); earliest still open at line {first}"
            ),
            "severity": "fatal",
        })
    for env, oline in env_stack:
        problems.append({
            "kind": "environment",
            "line": oline,
            "detail": rf"\begin{{{env}}} never closed",
            "severity": "fatal",
        })

    return problems


def format_structural_problems(problems: List[dict]) -> str:
    return "\n".join(
        f"  - line {p['line']}: {p['detail']}" for p in problems
    )


def fix_duplicate_label_colons(tex: str, arity: Dict[str, Tuple[int, bool]]) -> Tuple[str, int]:
    """
    Strip a trailing colon from the LABEL argument of two-argument bullet macros.

    Templates like Anubhav render \\resumeItem{#1}{#2} as \\textbf{#1}{: #2} —
    the macro supplies the ": " itself. An LLM writing
    \\resumeItem{Tech Stack:}{Python, FastAPI} therefore produces
    "Tech Stack:: Python, FastAPI". Observed in real output.

    Only touches macros whose first argument is a short label (no LaTeX
    commands, no sentence-length text), so a legitimate colon inside prose is
    left alone. Returns (tex, number_of_fixes).
    """
    fixes = 0
    for name, (nargs, has_opt) in arity.items():
        if mandatory_args(nargs, has_opt) < 2:
            continue
        pattern = re.compile(r"(\\" + re.escape(name) + r"\s*\{)([^{}]{1,60}?)\s*:\s*(\})")

        def repl(m):
            nonlocal fixes
            label = m.group(2)
            if "\\" in label:  # contains a command — leave it alone
                return m.group(0)
            fixes += 1
            return m.group(1) + label + m.group(3)

        tex = pattern.sub(repl, tex)
    return tex, fixes


def describe_macro_signatures(arity: Dict[str, Tuple[int, bool]]) -> str:
    """
    Render the true signatures for use in a prompt, so the LLM is told the
    template's real arities instead of the registry's hand-written guess.
    """
    if not arity:
        return ""
    lines = []
    for name in sorted(arity):
        nargs, has_opt = arity[name]
        need = mandatory_args(nargs, has_opt)
        sig = "\\" + name + ("[opt]" if has_opt else "") + "{arg}" * need
        lines.append(f"  {sig}   — {need} mandatory argument(s)")
    return "\n".join(lines)


def format_problems(problems: List[dict]) -> str:
    """One line per problem, for a repair prompt."""
    return "\n".join(
        f"  - line {p['line']}: \\{p['macro']} needs {p['expected']} argument(s) "
        f"but only {p['found']} was/were supplied → {p['snippet']}"
        for p in problems
    )
