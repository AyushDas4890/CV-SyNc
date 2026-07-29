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
