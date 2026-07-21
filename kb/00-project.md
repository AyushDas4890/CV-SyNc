# Project

RepoResume / CV-Sync: web app keep CV Projects section synced with GitHub repos.
User tag repos → fetch README+metadata → LLM write bullets → inject into LaTeX CV template → human approve diff → compile PDF.

Owner: Ayush (das.ayush4890@gmail.com), solo-intermediate dev. Teammate: Abhinav (github IamAbhinav01) — owns LaTeX compile service (DONE).

State (2026-07-21):
- compile service: DONE (see 03)
- auth service: DESIGNED, not coded (see 02)
- writer service: NEXT TO BUILD (see 04)
- fetch+LLM: designed only (see 05)
- CV format: LaTeX (Jake Gutierrez template), NOT docx — docx plan superseded.

Original README described CLI python tool (docxtpl). Project evolved: now microservices + LaTeX. Old README still describes: projects.json contract, notes-field-for-metrics idea, diff approval gate — all still valid concepts.
