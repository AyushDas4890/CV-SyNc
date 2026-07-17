# RepoResume

Semi-automated CV generator: tagged GitHub repos → LLM resume bullets → your CV template → PDF, with a diff + approval gate before anything is overwritten.

## Pipeline

```
tagged_repos.yaml → fetch.py (GitHub API) → data/raw/*.json
                  → summarize.py (OpenAI) → data/projects.json   ← the contract file
                  → fill.py (docxtpl)     → output/cv_filled.docx
                  → review.py (difflib)   → y/N gate
                  → convert.py (LibreOffice headless) → output/cv_final.pdf
```

## Setup (Windows)

1. Install Python 3.10+, Git, and [LibreOffice](https://libreoffice.org).
2. ```
   cd reporesume
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Fill `.env`:
   - `GITHUB_TOKEN` — https://github.com/settings/tokens → Generate new token (classic) → scope `public_repo`
   - `OPENAI_API_KEY` — https://platform.openai.com/api-keys
4. Edit `config/tagged_repos.yaml` — repos + metric notes (notes get woven into bullets).

## Run

```
python update_cv.py              # full run: fetch → summarize → fill → diff → approve → PDF
python update_cv.py --dry-run    # fetch + summarize only, writes data/projects.json
python update_cv.py --skip-fetch # reuse existing projects.json (no API calls)

# Ad-hoc repo links (overrides config list; repeatable; any owner):
python update_cv.py --repo https://github.com/AyushDas4890/Legal-Conflict-Resolver
python update_cv.py --repo owner/name --repo "https://github.com/u/r::91% accuracy notes here"
```

`config/tagged_repos.yaml` entries also accept full URLs:

```yaml
repos:
  - name: Legal-Conflict-Resolver        # bare name -> github_username
  - url: https://github.com/someone/else-repo
    notes: "used in production by 3 teams"
```

The diff shows old vs new Projects text; only `y` writes the PDF and updates the snapshot.

## Template

`cv/cv_template.docx` is the master. It was generated from the original CV by `cv/build_template.py` (run once; re-run if you want to regenerate it). The Projects section holds docxtpl/Jinja tags:

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

Edit styling in Word freely — just don't break a tag mid-edit (retype the whole tag if docxtpl reports "unexpected end of template"). `fill.py` renders with `autoescape=True` so `&`, `<`, `>` in data are safe.

## Contract: data/projects.json

```json
[{"title": "...", "tech_stack": ["..."], "bullets": ["..."], "repo_url": "..."}]
```

A sample is committed so the document half runs without API keys.

## Notes

- Never commit `.env` (already in `.gitignore`).
- Missing README on a repo → warning, pipeline continues.
- Invalid LLM JSON → one retry, then repo skipped with warning.
- `output/cv_final_sample.pdf` is a test render from the sample projects.json.
