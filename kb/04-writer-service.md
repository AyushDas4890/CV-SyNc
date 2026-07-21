# Writer service (TO BUILD — current work)

Job: projects.json → splice into LaTeX CV template → diff gate → send to compiler → PDF.

Template: Jake Gutierrez resume (sample in repo/user chat). ATS-clean already: single column, \pdfgentounicode=1, no images. Mark section: `% PROJECTS_START` / `% PROJECTS_END` comments around Projects section.

Generation surface — ONLY these 4 constructs for Projects:
```latex
\resumeSubHeadingListStart
\resumeProjectHeading{\textbf{Name} $|$ \emph{Tech, Tech}}{Dates}
\resumeItemListStart
  \resumeItem{bullet}
\resumeItemListEnd
\resumeSubHeadingListEnd
```

Renderer (deterministic code, NOT LLM):
1. validate projects.json shape, clear error on missing key
2. escape user text: & % $ # _ { } → \& \% \$ \# \_ \{ \}  (also ~ ^ \ if present)
3. emit blocks, splice between markers
4. POST to compiler /api/compile; relay PDF or 422 errors[]
5. 422 = renderer bug or bad template — fix in code, do NOT feed errors to LLM

Diff gate: store last-approved .tex snapshot. dry-run returns unified diff (text). approve endpoint = compile + overwrite snapshot. Reject = untouched. Default safe (N).

Planned API: POST /api/write {projects, dry?} , POST /api/approve.
Layout: same MVC as teammate repo (router/controller/service/config) — consistency.

Build steps + pass checks in 06-build-plan Phase A.
