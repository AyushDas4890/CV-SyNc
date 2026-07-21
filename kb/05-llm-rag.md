# Fetch + LLM half, RAG design

Fetch: GitHub API per tagged repo → README, languages, topics → data/raw/. V1: user paste repo links, ONE server PAT (.env) — public repos need no user auth, token only rate limit (60/hr→5000/hr). V2: GitHub OAuth "Connect GitHub", public_repo scope. Never ask users paste own PAT.

Summarize: OpenAI (gpt-4o-mini default) → projects.json. Rules: 2-3 action-verb bullets/project, MUST weave user `notes` metrics (accuracy, latency, users — git data lacks these). Invalid JSON → 1 retry → skip repo with warning. Output JSON ONLY, never LaTeX (renderer owns tex).

RAG (= retrieval into prompt, NOT fine-tuning):
| Corpus | Size | Method |
|---|---|---|
| A. template macro cheatsheet (4 macros + examples) | ~40 lines | prompt-stuff always, no retrieval |
| B. ATS rules (keywords, no tables/images, section names) | ~20 lines | prompt-stuff always |
| C. bullet exemplars, tagged ML/backend/frontend/devops | 100+, grows | embed text-embedding-3-small, query = repo langs+topics+README summary, top-5 |
| D. target job description (user pastes, optional) | per-req | chunk JD, retrieve tech-overlapping chunks, extract must-include keywords |

Storage: JSON file + precomputed embeddings + cosine (~20 lines) until corpus C >few thousand. Redis vector search if queryable needed. No vector DB yet.

Prompt assembly: [A+B] + [retrieved C exemplars + D keywords] + [repo data + notes] → JSON out.

Quality risk: corpus C decides bullet quality. Curate real strong bullets (verb+tech+metric), honest domain tags. Test: retrieve for own repo, eyeball 5 hits.

ATS vs images: CONFLICT. Images break ATS parsing. Decision pending (07): ATS-only, or two templates.
