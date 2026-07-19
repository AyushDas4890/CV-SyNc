# RepoResume

**Automated resume generation from your GitHub repositories.**

RepoResume keeps the *Projects* section of your CV in sync with your GitHub work. Tag the repos you care about, run one command, and the tool fetches each repo's README and metadata, asks an LLM to write clean resume bullets, injects them into your own CV template without touching its fonts, margins, or layout, converts the result to PDF — and shows you a before/after diff so nothing is ever overwritten without your approval.

```
┌─────────────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐   ┌─────────┐
│ tagged_repos.yaml│ → │ GitHub   │ → │ LLM        │ → │ docxtpl fill │ → │ diff +   │ → │ PDF     │
│ or --repo links  │   │ API fetch│   │ summarize  │   │ (template    │   │ approval │   │ export  │
│                  │   │          │   │            │   │  preserved)  │   │ gate     │   │         │
└─────────────────┘   └──────────┘   └────────────┘   └──────────────┘   └──────────┘   └─────────┘
                                     projects.json ← the contract file
```

## Features

- **Template preservation** — your CV stays a `.docx` master with Jinja placeholders; only the Projects section changes, byte-for-byte everything else survives.
- **LLM-written bullets** — README + languages + your own metric notes become 2–3 action-verb bullets per project (OpenAI, `gpt-4o-mini` by default).
- **Human review gate** — a unified diff of old vs. new content, `y/N` prompt; answering `n` leaves everything untouched.
- **Any repo, any owner** — tag repos in the config file or pass GitHub links on the command line.
- **Robust by default** — missing READMEs, invalid LLM JSON (one retry then skip), and API errors degrade gracefully instead of crashing the run.
- **PDF export** — Microsoft Word COM on Windows when available, LibreOffice headless otherwise.

## Requirements

- Python 3.10+
- Microsoft Word **or** [LibreOffice](https://www.libreoffice.org/) (for the PDF step)
- A GitHub personal access token and an OpenAI API key

## Installation

```bash
git clone https://github.com/<you>/reporesume.git
cd reporesume
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create `.env` in the project root (never commit it — it's in `.gitignore`):

```ini
GITHUB_TOKEN=ghp_...        # github.com/settings/tokens → classic token, scope: public_repo
OPENAI_API_KEY=sk-...       # platform.openai.com/api-keys
OPENAI_MODEL=gpt-4o-mini    # optional override
```

## Configuration

`config/tagged_repos.yaml` lists the repos that belong on your CV:

```yaml
github_username: AyushDas4890
repos:
  - name: Legal-Conflict-Resolver          # bare name → resolved against github_username
    notes: ">85% validation accuracy"      # real metrics the LLM must weave into bullets
  - url: https://github.com/someone/else-repo   # full links to any owner's repo also work
    notes: ""
```

The `notes` field matters: accuracy numbers, latency, user counts don't exist in git data — you supply them here and the LLM is instructed to include them.

## Usage

```bash
python update_cv.py                  # full run: fetch → summarize → fill → diff → approve → PDF
python update_cv.py --dry-run        # fetch + summarize only; writes data/projects.json and stops
python update_cv.py --skip-fetch     # reuse existing projects.json (no API calls)

# Ad-hoc repo links — overrides the config list, repeatable, any owner:
python update_cv.py --repo https://github.com/AyushDas4890/Legal-Conflict-Resolver
python update_cv.py --repo owner/name --repo "https://github.com/u/r::91% accuracy"
#                                            append ::text to attach notes ─┘
```

A run ends with a diff like:

```
--- current CV
+++ proposed CV
-Fine-tuned DeBERTa-v3-large on NLI data ...
+Fine-tuned DeBERTa-v3-large on NLI data achieving >85% validation accuracy ...

Apply these changes? [y/N]
```

Only `y` writes `output/cv_final.pdf` and updates the approval snapshot.

## Project structure

```
reporesume/
├── config/
│   └── tagged_repos.yaml     # which repos go on the CV
├── data/
│   ├── raw/                  # fetched repo data (gitignored)
│   └── projects.json         # the contract file: LLM output → template input
├── cv/
│   ├── cv_template.docx      # master template with docxtpl placeholders
│   ├── cv_original.pdf       # untouched original, for reference
│   └── build_template.py     # one-time generator for cv_template.docx
├── output/                   # cv_filled.docx, cv_final.pdf, snapshot (gitignored)
├── src/
│   ├── fetch.py              # GitHub API: README, languages, topics
│   ├── summarize.py          # OpenAI summarization + JSON contract validation
│   ├── fill.py               # docxtpl template fill (autoescape on)
│   ├── convert.py            # docx → PDF (Word COM / LibreOffice headless)
│   └── review.py             # difflib diff + y/N approval gate
├── update_cv.py              # single entry point
├── requirements.txt
└── .env                      # secrets — never committed
```

## The contract: `data/projects.json`

Everything upstream produces it; everything downstream consumes it. Shape:

```json
[
  {
    "title": "Legal Clause Conflict Resolver",
    "tech_stack": ["Python", "DeBERTa-v3", "FAISS", "FastAPI"],
    "bullets": ["Fine-tuned DeBERTa-v3-large on NLI data ...", "..."],
    "repo_url": "https://github.com/username/repo-name"
  }
]
```

A sample is committed so the document half runs without any API keys.

## Editing the template

The Projects section of `cv/cv_template.docx` contains docxtpl tags:

```
{%p for p in projects %}
{{ p.title }}
Tech: {{ p.tech_stack | join(", ") }}
{%p for b in p.bullets %}
{{ b }}
{%p endfor %}
{{ p.repo_url }}
{%p endfor %}
```

Restyle anything in Word freely. Two rules: type any tag in one uninterrupted go (Word splitting a tag internally causes docxtpl's "unexpected end of template" error — delete and retype the whole tag), and keep the bullet line in Word's bullet-list style so filled bullets render as proper list items.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `401` from GitHub | Token wrong or `.env` not loading — check `GITHUB_TOKEN` |
| `404` on a repo | Name/URL typo in config or `--repo` |
| "unexpected end of template" | Word split a docxtpl tag — retype it cleanly in the template |
| PDF fonts look wrong | LibreOffice substituted a missing font — install the template's fonts |
| Conversion hangs | Close any open LibreOffice window; the 60 s timeout will surface the error |
| Repo skipped with warning | LLM returned invalid JSON twice or repo has no usable content — rerun or add `notes` |

## Security

- `.env`, `venv/`, `data/raw/`, `output/` are gitignored.
- If a key ever leaks, revoke it immediately and generate a new one.
