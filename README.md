<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0A192F,100:F59E0B&height=220&section=header&text=CV-Sync&fontSize=70&fontColor=ffffff&fontAlignY=38&desc=GitHub%20repos%20%E2%86%92%20AI%20bullets%20%E2%86%92%20compiled%20PDF&descAlignY=58&descSize=20&animation=fadeIn" alt="CV-Sync banner" />

<img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=600&size=20&pause=1000&color=F59E0B&center=true&vCenter=true&width=780&lines=Tag+a+repo+%E2%86%92+AI+drafts+the+bullet;You+approve+the+diff+%E2%86%92+PDF+drops+out;The+LLM+never+touches+raw+LaTeX.+Ever." alt="Typing SVG" />

![status](https://img.shields.io/badge/status-active--development-orange?style=for-the-badge)
![stack](https://img.shields.io/badge/stack-Node%20%2F%20Express%20%2F%20React-0A192F?style=for-the-badge)
![cv-format](https://img.shields.io/badge/CV%20format-LaTeX-F59E0B?style=for-the-badge)
![license](https://img.shields.io/badge/license-unlicensed-lightgrey?style=for-the-badge)

</div>

---

## 🧠 The idea, in one breath

Your GitHub history is a better résumé writer than you are at 11pm the night before an application deadline. CV-Sync watches the repos you tag, pulls their README + language + topic metadata, asks an LLM to turn that into sharp, metric-aware bullet points, and — critically — **never lets the LLM anywhere near your actual LaTeX**. A deterministic renderer owns the `.tex`. The LLM only ever speaks JSON. You get a diff. You approve or reject it. Then it compiles to a real PDF.

```
   you                    CV-Sync                              you again
    │                        │                                     │
    │  tag repos             │                                     │
    ├───────────────────────▶│                                     │
    │                        │  fetch README + metadata (GitHub)   │
    │                        │  LLM → strict JSON bullets           │
    │                        │  splice into LaTeX template          │
    │                        │  compile → PDF or 422 errors         │
    │                        │◀─────────────── diff shown ──────────┤
    │  approve / reject      │                                     │
    ├───────────────────────▶│                                     │
    │                        │  compile final PDF                   │
    │◀───────── PDF ─────────┤                                     │
```

No image-based templates sneaking in unrendered LaTeX. No LLM hallucinating a `\begin{itemize}`. Just JSON in, PDF out, human veto power in the middle.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🧩 Architecture — four services, one contract

CV-Sync is deliberately **not** a monolith. Each half of the pipeline can be built, tested, and broken independently — which matters a lot when one half is being built by a teammate on the other side of a repo boundary.

```
┌──────────────┐   session cookie    ┌─────────────────────────────────────┐
│   Browser    │────────────────────▶│           Auth Service              │
│  (React/Vite)│                     │  GitHub OAuth + email/password       │
└──────┬───────┘                     │  Session (Redis) + MySQL users       │
       │                             └───────────────────┬───────────────────┘
       │ pick repos                                       │ guards every API
       ▼                                                   ▼
┌─────────────────────┐   projects.json    ┌─────────────────────────────────┐
│  Fetch + LLM Engine  │───────────────────▶│         Writer Service          │
│  GitHub API + RAG    │   (the contract)   │  splice → diff gate → compile   │
└─────────────────────┘                     └───────────────┬─────────────────┘
                                                              │ POST /api/compile
                                                              ▼
                                             ┌─────────────────────────────────┐
                                             │       Compiler Service          │
                                             │  latexmk in a texlive sandbox   │
                                             │  (built by teammate — done ✅)  │
                                             └───────────────┬─────────────────┘
                                                              │
                                                     PDF ◀────┘  or 422 + line-numbered errors
```

**The one rule that governs everything:** the LLM outputs JSON, never LaTeX. A deterministic renderer is the only thing allowed to write `.tex`. If the compiler throws a 422, it goes back to the renderer/developer — never back into the LLM's context. This is what keeps a resume from ever containing a hallucinated command injection into your own PDF.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🚦 Where things actually stand

| Piece | Status | Notes |
|---|---|---|
| 🔐 **Auth service** | ✅ Done (ahead of schedule) | GitHub OAuth (primary) + email/password (bcrypt) both live. Google OAuth code exists but is intentionally unmounted — "coming soon" |
| 🖨️ **Compiler service** | ✅ Done | Built by teammate [Abhinav](https://github.com/IamAbhinav01) — `CV_BUILDER`, Overleaf-style tex-in/PDF-out, sandboxed `latexmk` in a texlive Docker image |
| 🎨 **CV templates** | ✅ Done | 8 real, compile-tested LaTeX templates, multi-page preview rendering + page-count badges in the picker UI |
| ✍️ **Writer service** | 🚧 Next up | Splice `projects.json` into a Jake-Gutierrez-style template between `% PROJECTS_START/END` markers, diff-gate, forward to compiler |
| 🔎 **Fetch + LLM (RAG)** | 📐 Designed, not built | GitHub metadata fetch → OpenAI summarization → retrieval-augmented bullet generation |

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🗂️ What's actually in this repo

```
CV SYNC/
├── backend/
│   └── auth-service/            Session auth: GitHub OAuth + email/password, Redis sessions
│       ├── src/
│       │   ├── controllers/     githubAuth.controller.js, googleAuth.controller.js (unmounted)
│       │   ├── routes/          /api/auth/github, /email/login, /email/register, /me, /logout
│       │   └── services/        userStore.service.js — in-memory, keyed on github_id | google_id | email
│       └── .env                 GitHub OAuth App credentials
│
├── frontend/                    Vite + React onboarding flow
│   └── src/pages/
│       ├── AuthPage.jsx         GitHub button (primary) · Google (disabled) · email/pw form
│       ├── ExperiencePage.jsx
│       ├── GithubReposPage.jsx  repo picker
│       └── TemplatePage.jsx     8-template grid, multi-page preview modal, page-count badges
│
├── cv-templates/                8 real LaTeX CV templates, pulled from AyushDas4890/CV_TEMPLATES
│   ├── jake/ dphang/ anubhav/   compile with plain pdflatex
│   ├── altacv/ moderncv/        pdflatex + CTAN lato/roboto fonts
│   └── plushcv/ deedy/          xelatex (fontspec-based), bundled fonts
│   └── awesome-cv/
│
├── scripts/
│   └── render-template-previews.sh   compiles all 8 templates, rasterizes every page,
│                                       writes manifest.json (id → page count)
│
├── kb/                          Compressed knowledge base — architecture, decisions, build plan
│   ├── 00-project.md … 07-decisions.md
│   └── ui-reference/            static onboarding mockup (superseded, reference only)
│
└── docs/superpowers/
    ├── specs/                   design docs (spec-first, before any code)
    └── plans/                   bite-sized implementation plans
```

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🔒 The contracts that hold it together

**`projects.json`** — the handoff between the LLM half and the rendering half. This shape is the load-bearing wall of the whole system:

```json
[
  {
    "title": "Legal Clause Conflict Resolver",
    "tech_stack": ["Python", "DeBERTa-v3", "FAISS", "FastAPI"],
    "bullets": [
      "Fine-tuned DeBERTa-v3-large on an NLI dataset, reaching 87%+ validation accuracy.",
      "Cut vector-search query latency 45% by optimizing the FAISS retrieval pipeline."
    ],
    "repo_url": "https://github.com/AyushDas4890/Legal-Conflict-Resolver",
    "dates": "Jan 2026 – Present"
  }
]
```

**Compiler API** (`POST /api/compile`) — the boundary between "text" and "PDF":

| Response | Meaning |
|---|---|
| `200` | Binary `application/pdf` — it compiled |
| `422` | `{ ok: false, log, errors: [{file, line, message}] }` — LaTeX error, max 10 reported |
| `400` | `tex` field missing from request |
| `413` | `tex` over 2,000,000 characters |

Sandboxed via `latexmk -pdf -interaction=nonstopmode -halt-on-error -no-shell-escape`, `openin_any=p openout_any=p` (paranoid file access), hard 15s timeout, job directory nuked after every run — win or lose.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🧬 The RAG design (fetch + LLM half)

Retrieval, not fine-tuning. Four corpora, stuffed and retrieved differently:

| Corpus | What it is | How it's used |
|---|---|---|
| **A.** Template macro cheatsheet | ~40 lines, the 4 LaTeX constructs the renderer understands | Always prompt-stuffed, no retrieval |
| **B.** ATS rules | Keyword hygiene, no tables/images, correct section names | Always prompt-stuffed |
| **C.** Bullet exemplars | 100+ tagged (ML / backend / frontend / devops), growing | Embedded (`text-embedding-3-small`), top-5 retrieved per repo |
| **D.** Target job description | User-pasted, optional | Chunked, tech-overlap retrieval, keyword extraction |

`[A + B] + [retrieved C exemplars + D keywords] + [repo data + your notes] → strict JSON out.` No vector DB yet — a JSON file of precomputed embeddings and cosine similarity is enough until corpus C grows into the thousands.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🔐 How auth actually works

Session-based, not JWT — a deliberate, locked decision. The cookie holds **only** an opaque `session_id`; everything else lives server-side in Redis.

```
signup/login → argon2id / bcrypt verify → Redis session (TTL) → Set-Cookie (last step, always)
protected route → cookie → session_id → Redis lookup → 200 or 401
logout → DELETE Redis session (not just the cookie) → clear cookie
```

GitHub OAuth is the **primary, recommended** login path — not a bolt-on. Email/password (bcrypt, 12 rounds) works as a full alternative. Google OAuth is implemented but its routes are deliberately left unmounted (`"coming soon"` in the UI) — finding it disconnected in the code is a feature, not a bug.

No user enumeration: a login attempt against a non-existent email still runs a dummy argon2 verification and returns the exact same generic 401 as a wrong password, in the same rough time window.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## ⚡ Running it locally

**Prerequisites:** Node 18+, Redis, a registered GitHub OAuth App (callback URL must match `.env` exactly).

```bash
# 1. Auth service
cd backend/auth-service
npm install
npm run dev              # → "auth-service listening on :4000"
# needs Redis reachable locally — no Redis means session routes 503
# (that's the coded fallback working, not a crash)

# 2. Frontend
cd frontend
npm install
npm run dev               # → http://localhost:5173
```

**Regenerating template previews** (after touching anything in `cv-templates/`):

```bash
./scripts/render-template-previews.sh
# compiles all 8 templates, rasterizes every page @150dpi,
# writes frontend/public/template-previews/{id}.png, {id}-p2.png, ...
# + manifest.json mapping id → page count
```

Requires `pdflatex`, `xelatex`, and `pdftoppm` (poppler-utils) on `PATH`.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🎯 Design principles worth knowing before you touch this code

- **The LLM never writes LaTeX.** Ever. It writes JSON; a deterministic renderer owns every `\` in the output.
- **There is always a diff gate.** No AI-authored change lands in your CV without a human seeing the diff first. Reject leaves everything untouched, and reject is the default.
- **Compile errors are a renderer bug, not an LLM problem.** A 422 from the compiler routes back to the code, never back into an LLM prompt.
- **Session auth, not JWT.** Revocation should mean something. Logout destroys the Redis session, not just the cookie.
- **Static, pre-rendered previews over live rendering.** Template previews are compiled once and committed as PNGs — no LaTeX toolchain needed at runtime just to show a picker grid.

---

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:0A192F,100:1a2942&height=3" />

## 🙋 Open questions (ask before assuming)

- Images vs. ATS-safe text-only CVs — genuinely unresolved, might end up as two template tracks.
- Writer service: Node (assumed) or Python? Same repo, or its own?
- What happens the instant after a user clicks a template in the picker — no backend call exists yet; it's local React state until the writer service exists to receive it.

---

<div align="center">

*Built by [Ayush](mailto:das.ayush4890@gmail.com) · compiler service by [Abhinav](https://github.com/IamAbhinav01)*

**No LLM was allowed to write LaTeX in the making of this project.** 🙂

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0A192F,100:F59E0B&height=120&section=footer" />

</div>
