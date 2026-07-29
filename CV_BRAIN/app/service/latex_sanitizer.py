"""
LaTeX sanitizer — post-processing utilities to clean up LLM-generated LaTeX.
Extracted from the original main.py with no logic changes.
"""

import re
from typing import List
from app.models import UserProfile, RepoDetail


def escape_latex(text: str) -> str:
    """Sanitize and escape special LaTeX characters in plain text string."""
    if not isinstance(text, str):
        return text

    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
    }

    pattern = re.compile(r'(?<!\\)([&%$#_])')
    return pattern.sub(lambda m: chars.get(m.group(1), m.group(1)), text)


def fix_href_extra_braces(line: str) -> str:
    """
    Finds \\href{...}{...} in a line and checks if there's an extra trailing '}'.
    It correctly handles nested braces inside the arguments (like \\underline{...}).
    """
    if r'\href{' not in line:
        return line

    # Only act when the line actually has MORE closing braces than opening
    # ones. Without this guard the function treated the closing brace of an
    # enclosing group as "extra": `{\href{url}{Label}}` and
    # `\namesection{A}{B}{\href{url}{Label}}` both lost their outer brace,
    # which made Deedy and PlushCV die with
    # "File ended while scanning use of \namesection".
    if line.count("}") <= line.count("{"):
        return line

    idx = 0
    while True:
        idx = line.find(r'\href{', idx)
        if idx == -1:
            break
        
        # We found \href{. Let's find the end of the first argument.
        # Start scanning after '\href{' (which is length 6)
        first_arg_start = idx + 6
        depth = 1
        i = first_arg_start
        while i < len(line) and depth > 0:
            if line[i] == '{':
                depth += 1
            elif line[i] == '}':
                depth -= 1
            i += 1
            
        if depth > 0 or i >= len(line) or line[i] != '{':
            # Could not find the second argument start '{', or scanning failed.
            idx += 6
            continue
            
        # Found '{' for the second argument. Let's find its closing brace.
        second_arg_start = i + 1
        depth = 1
        i = second_arg_start
        while i < len(line) and depth > 0:
            if line[i] == '{':
                depth += 1
            elif line[i] == '}':
                depth -= 1
            i += 1
            
        if depth > 0:
            idx += 6
            continue
            
        # We are now right after the second argument's closing brace.
        # Check if the next character is '}'.
        if i < len(line) and line[i] == '}':
            # This is an extra closing brace! Remove it.
            line = line[:i] + line[i+1:]
            idx = i
        else:
            idx = i
            
    return line


# Environments where `&` is a real alignment tab and must NOT be escaped.
_ALIGN_ENVS = {
    "tabular", "tabular*", "tabularx", "longtable", "array", "align", "align*",
    "aligned", "matrix", "pmatrix", "bmatrix", "vmatrix", "cases", "split",
    "eqnarray", "eqnarray*", "supertabular", "tabu",
}

# Commands whose FIRST argument is a URL: raw `&` and `_` must survive there.
_URL_COMMANDS = {"href", "url", "hyperref", "nolinkurl"}

_CMD_RE = re.compile(r"\\([A-Za-z@]+)\*?")


def _brace_group_end(text: str, i: int) -> int:
    """Index just past the {...} group starting at i, or i if none."""
    if i >= len(text) or text[i] != "{":
        return i
    depth = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def escape_body_specials(tex: str) -> str:
    """
    Escape bare `&` and `_` in document-body TEXT, including inside macro
    arguments.

    The previous approach escaped line by line and skipped any line starting
    with a known TeX command. Since virtually every content line starts with
    \\resumeItem, \\cvitem and friends, specials inside macro ARGUMENTS were
    never escaped at all — a real compile died on
    `\\resumeItem{Interview Prep.}{... 730+ Q&A boxes ...}` with
    "Misplaced alignment tab character &".

    Walks the body character by character and skips the places where these
    characters are legitimate:
      - math mode (`$...$`), where `_` is a subscript
      - alignment environments, where `&` is a column separator
      - URL arguments of \\href/\\url, which must keep raw `&` and `_`
      - comments
      - already-escaped `\\&` / `\\_`
    """
    if not isinstance(tex, str):
        return tex

    start = tex.find(r"\begin{document}")
    if start < 0:
        return tex

    head, body = tex[:start], tex[start:]
    out = []
    i = 0
    math = False
    env_stack = []

    while i < len(body):
        ch = body[i]

        if ch == "\\":
            m = _CMD_RE.match(body, i)
            if not m:
                # Escaped character such as \& \_ \% — copy both chars as-is.
                out.append(body[i : i + 2])
                i += 2
                continue

            name = m.group(1)
            out.append(body[i : m.end()])
            i = m.end()

            if name in ("begin", "end"):
                j = i
                while j < len(body) and body[j] in " \t":
                    j += 1
                end = _brace_group_end(body, j)
                if end > j:
                    env = body[j + 1 : end - 1].strip()
                    if name == "begin":
                        env_stack.append(env)
                    elif env_stack and env_stack[-1] == env:
                        env_stack.pop()
                    out.append(body[i:end])
                    i = end
            elif name in _URL_COMMANDS:
                j = i
                while j < len(body) and body[j] in " \t":
                    j += 1
                end = _brace_group_end(body, j)
                if end > j:
                    # Copy the URL verbatim; the label argument that follows is
                    # ordinary text and keeps being processed normally.
                    out.append(body[i:end])
                    i = end
            continue

        if ch == "%":
            nl = body.find("\n", i)
            nl = len(body) if nl < 0 else nl + 1
            out.append(body[i:nl])
            i = nl
            continue

        if ch == "$":
            math = not math
            out.append(ch)
            i += 1
            continue

        if ch == "&" and not math and not (env_stack and env_stack[-1] in _ALIGN_ENVS):
            out.append(r"\&")
            i += 1
            continue

        if ch == "_" and not math:
            out.append(r"\_")
            i += 1
            continue

        out.append(ch)
        i += 1

    return head + "".join(out)


def sanitize_generated_tex(tex: str) -> str:
    """Clean up markdown code blocks, duplicate package includes, empty list
    environments, trailing linebreaks, and unescaped underscores/ampersands."""
    if not isinstance(tex, str):
        return ""

    # 1. Clean markdown code wraps if present
    tex = re.sub(r"^```(?:latex|tex)?\n", "", tex.strip(), flags=re.MULTILINE)
    tex = re.sub(r"\n```$", "", tex.strip(), flags=re.MULTILINE)
    tex = tex.strip()

    # 1b. Strip any natural language text before the actual LaTeX content
    doc_class_idx = tex.find(r'\documentclass')
    if doc_class_idx >= 0:
        tex = tex[doc_class_idx:]
    else:
        # Fall back to comment symbol only if near the beginning of the response
        comment_idx = tex.find('%')
        if 0 <= comment_idx < 500:
            tex = tex[comment_idx:]
    tex = tex.strip()

    # 2. Fix conflicting FontAwesome packages
    if r"\usepackage{fontawesome}" in tex and r"\usepackage{fontawesome5}" in tex:
        tex = tex.replace(
            r"\usepackage{fontawesome}",
            r"% \usepackage{fontawesome} (removed duplicate)",
        )

    # 3. Fix underscores in \href{URL}{LABEL} URLs using string parsing.
    def fix_href_urls(text):
        result = []
        i = 0
        marker = '\\href{'
        while i < len(text):
            pos = text.find(marker, i)
            if pos == -1:
                result.append(text[i:])
                break
            result.append(text[i:pos])
            j = pos + len(marker)
            url_start = j
            while j < len(text) and text[j] != '}':
                j += 1
            url = text[url_start:j]
            url_fixed = url.replace('\\_', '_')
            result.append(marker + url_fixed)
            i = j
        return ''.join(result)

    tex = fix_href_urls(tex)

    # 3b. Escape literal &/_ inside section-heading command arguments.
    # These commands are skipped by the per-line escaping pass below (they're
    # TeX commands, not body text), but their brace argument IS free text
    # (e.g. \cvsection{Achievements & Honors}) and must still be escaped —
    # an unescaped & there is a fatal "Misplaced alignment tab character".
    def escape_heading_arg(match):
        cmd, arg = match.group(1), match.group(2)
        arg = re.sub(r'(?<!\\)&', r'\&', arg)
        arg = re.sub(r'(?<!\\)_', r'\_', arg)
        return f'{cmd}{{{arg}}}'

    tex = re.sub(
        r'(\\(?:section|subsection|cvsection)\*?)\{([^{}]*)\}',
        escape_heading_arg,
        tex,
    )

    # 4. Process line by line for character escaping & deduplication
    lines = tex.split('\n')
    seen_packages = set()
    cleaned_lines = []
    past_begin_doc = False

    for line in lines:
        # Apply brace balancing for href
        line = fix_href_extra_braces(line)
        stripped = line.strip()


        if r'\begin{document}' in stripped:
            past_begin_doc = True

        # Deduplicate packages
        if stripped.startswith(r"\usepackage{fontawesome") or stripped.startswith(
            r"\usepackage{fontawesome5"
        ):
            if stripped in seen_packages:
                continue
            seen_packages.add(stripped)

        # NOTE: the per-line escaping that used to live here skipped any line
        # starting with a known TeX command. Since nearly every content line
        # starts with \resumeItem / \cvitem / etc., specials inside macro
        # ARGUMENTS were never escaped — which is how "730+ Q&A boxes" reached
        # the compiler and died with "Misplaced alignment tab character &".
        # Escaping is now done by escape_body_specials() below, which walks the
        # body and understands math mode, alignment environments and URLs.

        cleaned_lines.append(line)

    res_tex = '\n'.join(cleaned_lines)

    # 5. Remove empty list environments
    res_tex = re.sub(
        r"\\resumeSubHeadingListStart\s*\\resumeSubHeadingListEnd", "", res_tex
    )
    res_tex = re.sub(r"\\resumeItemListStart\s*\\resumeItemListEnd", "", res_tex)
    res_tex = re.sub(
        r"\\begin\{itemize\}(?:\[[^\]]*\])?\s*\\end\{itemize\}", "", res_tex
    )

    # 5b. Remove itemize blocks that contain NO \item — even if they hold
    # other tokens (e.g. \parskip=0.1em). An itemize with settings but no
    # \item is fatal: "Something's wrong--perhaps a missing \item." This
    # happens when a section (e.g. Experience) has no data to fill. Skip
    # blocks with nested itemize to avoid mismatching on the non-greedy span.
    def drop_itemless_itemize(match):
        body = match.group(1)
        if r'\begin{itemize}' in body:
            return match.group(0)  # nested — leave for a later pass
        # Never span a macro definition. Jake's preamble defines
        #   \newcommand{\resumeSubHeadingListStart}{\begin{itemize}[...]}
        #   \newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
        # and this DOTALL match happily ran from the \begin in one definition
        # to the \end in the other, emptying both. Only the later
        # replace_preamble_with_original() call was hiding the damage.
        if r'\newcommand' in body or r'\renewcommand' in body:
            return match.group(0)
        return '' if r'\item' not in body else match.group(0)

    res_tex = re.sub(
        r"\\begin\{itemize\}(?:\[[^\]]*\])?(.*?)\\end\{itemize\}",
        drop_itemless_itemize,
        res_tex,
        flags=re.DOTALL,
    )

    # 6. Remove empty skill lines like \textbf{Databases}{: } \\
    res_tex = re.sub(r"\\textbf\{[^}]+\}\{:\s*\}\s*(\\\\)?", "", res_tex)

    # 7. Remove trailing \\ before closing braces or \end{itemize}
    res_tex = re.sub(r"\\\\\s*(\}\s*\\end\{itemize\})", r"\1", res_tex)
    res_tex = re.sub(r"\\\\\s*(\}\s*\})", r"\1", res_tex)

    # 7b. Remove stray \\ that has no line to end — a classic fatal
    # "There's no line here to end." A forced linebreak is only valid after
    # actual content on the same line, so strip \\ when it (a) sits alone on
    # its own line, or (b) directly follows a section header / \begin{...} /
    # blank line, where there is nothing preceding it to break.
    res_tex = re.sub(r"(?m)^[ \t]*\\\\[ \t]*$\n?", "", res_tex)
    res_tex = re.sub(
        r"(\\(?:section|subsection|cvsection)\*?\{[^{}]*\}|\\begin\{[^{}]*\})\s*\\\\",
        r"\1",
        res_tex,
    )

    # 8. Remove empty sections with no items
    res_tex = re.sub(
        r"\\section\{[^}]+\}\s*(?=\\section|\n\\end\{document\})", "", res_tex
    )

    # 9. REMOVED — \resumeSubheading argument "fixing".
    #
    # It collected arguments with re.findall(r'\{[^{}]*\}'), which cannot see
    # nested braces. Given
    #     \resumeSubheading{Lovely Professional University}{Punjab}
    #                      {B.Tech \textbf{CSE}}{2023 -- 2027}
    # it matched only the first two groups, padded to four with EMPTY braces,
    # and left the real third and fourth arguments dangling as stray text:
    #     {Lovely...}{Punjab}{}{}{B.Tech \textbf{CSE}}{2023 -- 2027}
    # So the degree and dates silently vanished from the rendered CV — a
    # content-destroying bug that did not always announce itself as a compile
    # error.
    #
    # Wrong argument counts are now handled properly by
    # macro_validator.check_macro_calls, which brace-matches correctly, works
    # for every macro in every template, and repairs via a targeted LLM pass.

    # Escape bare & and _ in body text, including inside macro arguments.
    # Runs last so earlier structural passes see the text unmodified.
    res_tex = escape_body_specials(res_tex)

    return res_tex


def replace_preamble_with_original(edited_tex: str, template_tex: str) -> str:
    """
    Force-replace the LLM's preamble with the original template preamble.
    The LLM often drops/modifies \\newcommand definitions, causing
    'Undefined control sequence' errors.
    """
    begin_doc_marker = r'\begin{document}'
    orig_preamble_idx = template_tex.find(begin_doc_marker)
    llm_body_idx = edited_tex.find(begin_doc_marker)

    if orig_preamble_idx > 0 and llm_body_idx > 0:
        original_preamble = template_tex[:orig_preamble_idx]
        llm_body = edited_tex[llm_body_idx:]
        edited_tex = original_preamble + llm_body
        print("[LLM_BRAIN] Preamble replaced with original template preamble (macros guaranteed).")

    return edited_tex


def fallback_latex_filler(
    tex: str,
    user: UserProfile,
    repos: List[RepoDetail],
    has_experience: bool,
    has_education: bool,
) -> str:
    """Fallback deterministic filler when no LLM API key is present or LLM fails."""
    result = tex

    name = escape_latex(user.name or "Candidate Name")
    email = escape_latex(user.email or "user@example.com")

    # Direct replacements for known template placeholders
    placeholders_name = ["Jake Ryan", "Sourabh Bajaj", "Danny Phang", "Zachary Deedy", "Claud D. Park", "John Doe", "First Last", "Candidate Name"]
    for p_name in placeholders_name:
        result = result.replace(p_name, name)

    placeholders_email = ["jake@su.edu", "sourabh@sourabhbajaj.com", "email@example.com", "x@x.com", "user@example.com"]
    for p_email in placeholders_email:
        result = result.replace(p_email, email)

    # Command-based replacements for standard resume macros (extremely robust fallback)
    result = re.sub(r"(\\name\{)[^}]*(})", rf"\1{name}\2", result)
    result = re.sub(r"(\\email\{)[^}]*(})", rf"\1{email}\2", result)
    result = re.sub(r"(\\phone(?:\[[^\]]*\])?\{)[^}]*(})", rf"\1{escape_latex(user.phone or '')}\2", result)
    result = re.sub(r"(\\linkedin\{)[^}]*(})", rf"\1{escape_latex(user.linkedin or '')}\2", result)
    result = re.sub(r"(\\github\{)[^}]*(})", rf"\1{escape_latex(user.github or '')}\2", result)
    result = re.sub(r"(\\location\{)[^}]*(})", rf"\1{escape_latex(user.location or '')}\2", result)
    result = re.sub(r"(\\homepage\{)[^}]*(})", rf"\1{escape_latex(user.portfolio or '')}\2", result)

    # Basic header replacements (backup regex for href mailto)
    result = re.sub(
        r"(\\href\{mailto:[^}]*\}\{)[^}]*(})", rf"\1{email}\2", result
    )

    # If experience is empty, remove experience section
    if not has_experience:
        result = re.sub(
            r"\\section\{Experience\}.*?(?=\\section|\n\\end\{document\})",
            "",
            result,
            flags=re.DOTALL | re.IGNORECASE,
        )
        result = re.sub(
            r"\\section\{Work Experience\}.*?(?=\\section|\n\\end\{document\})",
            "",
            result,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # If education is empty, remove education section
    if not has_education:
        result = re.sub(
            r"\\section\{Education\}.*?(?=\\section|\n\\end\{document\})",
            "",
            result,
            flags=re.DOTALL | re.IGNORECASE,
        )

    return result
