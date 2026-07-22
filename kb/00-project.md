# Project

RepoResume / CV-Sync: web app keep CV Projects section synced with GitHub repos.
User tag repos → fetch README+metadata → LLM write bullets → inject into LaTeX CV template → human approve diff → compile PDF.

Owner: Ayush (das.ayush4890@gmail.com), solo-intermediate dev. Teammate: Abhinav (github IamAbhinav01) — owns LaTeX compile service (DONE) and originally hosted CV_BRAIN; Ayush now also has contributor/push access to both his repos.

State (2026-07-22):
- compile service (CV_BUILDER): DONE (see 03) — lives at github.com/IamAbhinav01/CV_BUILDER, NOT vendored into this repo (Node/Express, Abhinav's)
- CV_BRAIN (LLM generation service): DONE and vendored into this repo at `CV_BRAIN/` — Python/FastAPI, generates full .tex directly via LLM (see 07-decisions.md — supersedes the old writer-svc/projects.json design below). Originally github.com/IamAbhinav01/CV_BRAIN; Ayush pushed the achievements+OpenAI patch there directly (commit f5e3417) then copied the result in here so frontend+backend+LLM service sit together in one place.
- auth service: DONE — GitHub OAuth + email/password, session-based, in-memory userStore (see 02); now also fetches repo READMEs/topics for CV_BRAIN
- frontend onboarding: DONE — 5-step flow (auth → profile → experience → github-repos → template picker) → generate (CV_BRAIN) → compile (CV_BUILDER) → download PDF, all wired end-to-end
- profile+education store: DONE — POST/GET /api/profile persists studentProfile on user object, localStorage cache mirrors it (see 02)
- writer service (projects.json + splice-into-template + diff gate): SUPERSEDED, never built — CV_BRAIN does LLM→tex directly instead (see 07-decisions.md). The diff/approve gate from that design is a still-open gap in the CV_BRAIN path.
- fetch+LLM: DONE differently than originally designed — CV_BRAIN + auth-service's README-fetch endpoint, not the standalone RAG design in 05 (05 is now historical context, not the shipped design)
- CV format: LaTeX (Jake Gutierrez template + 7 others), NOT docx — docx plan superseded.

Original README described CLI python tool (docxtpl). Project evolved: now microservices + LaTeX. Old README still describes: projects.json contract, notes-field-for-metrics idea, diff approval gate — all still valid concepts.
