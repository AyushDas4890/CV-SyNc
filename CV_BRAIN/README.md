# 🧠 LLM Brain — ATS Resume & LaTeX Generation Engine

LLM Brain is the AI core of the CV-SyNc pipeline. It takes a **template ID + user data**, fetches the LaTeX template from CV_BUILDER, fills it with real user data via an LLM (Groq/OpenAI), validates the output for completeness, and returns compilable LaTeX.

---

## Architecture

```
Frontend (CV-SyNc)
    │
    ▼  POST /api/generate-cv  {user_profile, template_id, selected_repos}
┌──────────────┐
│  LLM_BRAIN   │──── GET /api/templates/:id/full ────▶ CV_BUILDER (:3000)
│   (:8000)    │◀── {tex: "concatenated .tex"} ──────┘
│              │
│  1. Lookup template registry (engine, macros)
│  2. Build template-aware system prompt
│  3. Call LLM (Groq → OpenAI fallback)
│  4. Validate output completeness
│  5. Retry once if validation fails
│  6. Sanitize + preamble-swap
│              │
│              │──▶ {ok: true, tex: "...", engine: "pdflatex"}
└──────────────┘
```

---

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** (Python package manager)
- **CV_BUILDER** running on port `3000` (needed for template fetching)
- **Groq API Key** (free tier at [console.groq.com](https://console.groq.com))

---

## Setup

### 1. Install dependencies

```bash
cd LLM_BRAIN
uv sync
```

### 2. Configure environment

Edit `.env` file:

```env
PORT=8000
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TEMPERATURE=0.1
GROQ_MAX_TOKENS=8192
CV_BUILDER_URL=http://localhost:3000

# Optional: OpenAI fallback
# OPENAI_API_KEY=sk-...
```

### 3. Start CV_BUILDER first (required)

```bash
cd ../CV_BUILDER
npm install
npm start
# ✅ Running on http://localhost:3000
```

### 4. Start LLM Brain

```bash
cd ../LLM_BRAIN
uv run python main.py
# ✅ Uvicorn running on http://0.0.0.0:8000
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `GET`  | `/api/templates` | List all supported templates with engine info |
| `POST` | `/api/generate-cv` | Generate a CV from user data + template |

---

## Testing

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"ok": true, "service": "LLM Brain"}
```

---

### 2. List Available Templates

```bash
curl http://localhost:8000/api/templates
```

**Expected:** Returns 8 templates with their compilation engines:

```json
{
  "ok": true,
  "templates": [
    {"id": "Jake_s_Resume__3_", "display_name": "Jake's Resume", "engine": "pdflatex", ...},
    {"id": "AltaCV_Template__1_", "display_name": "AltaCV", "engine": "lualatex", ...},
    {"id": "Deedy_CV__1_", "display_name": "Deedy CV", "engine": "xelatex", ...},
    {"id": "Awesome_CV__3_", "display_name": "Awesome CV", "engine": "xelatex", ...},
    {"id": "PlushCV__2_", "display_name": "PlushCV", "engine": "xelatex", ...},
    {"id": "ModernCV_and_Cover_Letter_Template__2_", "display_name": "ModernCV", "engine": "pdflatex", ...},
    {"id": "Resume_Template_by_Anubhav__2_", "display_name": "Anubhav Resume", "engine": "pdflatex", ...},
    {"id": "dphang_CV_Template__1_", "display_name": "dphang CV", "engine": "pdflatex", ...}
  ]
}
```

---

### 3. Generate a CV (Full Test)

#### PowerShell

```powershell
$body = @{
    user_profile = @{
        name = "Abhinav Kumar"
        email = "abhinav@example.com"
        phone = "+91-9876543210"
        location = "Bangalore, India"
        linkedin = "linkedin.com/in/abhinav"
        github = "github.com/abhinav"
        portfolio = "abhinav.dev"
        summary = "Full-stack developer with 2 years of experience building scalable web applications using React, Node.js, and Python."
        education = @(
            @{
                institution = "Indian Institute of Technology"
                degree = "B.Tech in Computer Science"
                location = "New Delhi, India"
                dates = "Aug 2020 -- May 2024"
                gpa = "8.5/10"
            }
        )
        experience = @(
            @{
                company = "TechCorp Solutions"
                role = "Software Engineer Intern"
                location = "Bangalore, India"
                dates = "May 2023 -- Aug 2023"
                bullets = @(
                    "Built a real-time notification microservice using Node.js and Redis, reducing delivery latency by 40%",
                    "Developed REST APIs for user management module serving 10K+ daily active users",
                    "Implemented CI/CD pipeline using GitHub Actions, cutting deployment time from 30 min to 5 min"
                )
            }
        )
        skills = @{
            Languages = "Python, JavaScript, TypeScript, Java, SQL"
            Frameworks = "React, Next.js, Node.js, Express, FastAPI, Django"
            Tools = "Git, Docker, AWS, PostgreSQL, MongoDB, Redis"
            Concepts = "REST APIs, Microservices, CI/CD, Agile, System Design"
        }
        certifications = @(
            "AWS Cloud Practitioner (2024)",
            "Meta Front-End Developer Certificate (2023)"
        )
    }
    selected_repos = @(
        @{
            name = "cv-sync"
            description = "A full-stack resume builder that syncs GitHub projects into LaTeX templates with AI-powered content generation"
            language = "JavaScript"
            topics = @("react", "nodejs", "latex", "resume-builder")
            url = "https://github.com/abhinav/cv-sync"
            readme_content = "# CV-SyNc`nA modern resume builder that connects to your GitHub, analyzes your repositories, and generates ATS-optimized LaTeX resumes.`n`n## Features`n- OAuth GitHub login`n- Repository analysis with README parsing`n- 8 LaTeX templates with live preview`n- AI-powered content generation via Groq/OpenAI`n`n## Tech Stack`n- Frontend: React + Vite`n- Backend: Node.js + Express`n- AI: FastAPI + LangChain + Groq"
            user_notes = "Led the full architecture design and implemented the AI pipeline end-to-end"
        },
        @{
            name = "realtime-chat"
            description = "WebSocket-based real-time chat application with rooms, typing indicators, and message persistence"
            language = "TypeScript"
            topics = @("websocket", "react", "nodejs", "mongodb")
            url = "https://github.com/abhinav/realtime-chat"
            readme_content = "# Realtime Chat`nA scalable chat application built with Socket.io, React, and MongoDB.`n`n## Features`n- Real-time messaging with WebSockets`n- Chat rooms with user presence`n- Typing indicators`n- Message history with pagination`n- JWT authentication"
            user_notes = "Built this to learn WebSocket architecture and real-time systems"
        }
    )
    template_id = "Jake_s_Resume__3_"
    target_role = "Full Stack Developer"
    target_pages = 1
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://localhost:8000/api/generate-cv `
    -Method POST `
    -ContentType "application/json" `
    -Body $body | ConvertTo-Json -Depth 3
```

#### curl (Linux/Mac)

```bash
curl -X POST http://localhost:8000/api/generate-cv \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
        "name": "Abhinav Kumar",
        "email": "abhinav@example.com",
        "phone": "+91-9876543210",
        "location": "Bangalore, India",
        "linkedin": "linkedin.com/in/abhinav",
        "github": "github.com/abhinav",
        "portfolio": "abhinav.dev",
        "summary": "Full-stack developer with 2 years of experience building scalable web applications using React, Node.js, and Python.",
        "education": [{
            "institution": "Indian Institute of Technology",
            "degree": "B.Tech in Computer Science",
            "location": "New Delhi, India",
            "dates": "Aug 2020 -- May 2024",
            "gpa": "8.5/10"
        }],
        "experience": [{
            "company": "TechCorp Solutions",
            "role": "Software Engineer Intern",
            "location": "Bangalore, India",
            "dates": "May 2023 -- Aug 2023",
            "bullets": [
                "Built a real-time notification microservice using Node.js and Redis, reducing delivery latency by 40%",
                "Developed REST APIs for user management module serving 10K+ daily active users",
                "Implemented CI/CD pipeline using GitHub Actions, cutting deployment time from 30 min to 5 min"
            ]
        }],
        "skills": {
            "Languages": "Python, JavaScript, TypeScript, Java, SQL",
            "Frameworks": "React, Next.js, Node.js, Express, FastAPI, Django",
            "Tools": "Git, Docker, AWS, PostgreSQL, MongoDB, Redis"
        },
        "certifications": ["AWS Cloud Practitioner (2024)"]
    },
    "selected_repos": [{
        "name": "cv-sync",
        "description": "Full-stack resume builder that syncs GitHub projects into LaTeX templates",
        "language": "JavaScript",
        "topics": ["react", "nodejs", "latex"],
        "url": "https://github.com/abhinav/cv-sync",
        "readme_content": "# CV-SyNc\nModern resume builder with GitHub integration and AI content generation.\n\n## Tech Stack\n- React + Vite\n- Node.js + Express\n- FastAPI + LangChain",
        "user_notes": "Led architecture design and AI pipeline"
    }],
    "template_id": "Jake_s_Resume__3_",
    "target_role": "Full Stack Developer",
    "target_pages": 1
}'
```

#### Expected Response

```json
{
  "ok": true,
  "tex": "% Resume in Latex\n\\documentclass[letterpaper,11pt]{article}\n...(full LaTeX)...\\end{document}",
  "engine": "pdflatex",
  "template_id": "Jake_s_Resume__3_",
  "summary": "Resume generated successfully with template-aware prompting and completeness validation."
}
```

---

### 4. Test with Different Templates

Just change `template_id` in the request body:

```json
{"template_id": "Deedy_CV__1_"}          // → engine: xelatex
{"template_id": "AltaCV_Template__1_"}   // → engine: lualatex
{"template_id": "Awesome_CV__3_"}        // → engine: xelatex
{"template_id": "PlushCV__2_"}           // → engine: xelatex
{"template_id": "ModernCV_and_Cover_Letter_Template__2_"}  // → engine: pdflatex
{"template_id": "Resume_Template_by_Anubhav__2_"}         // → engine: pdflatex
{"template_id": "dphang_CV_Template__1_"}                  // → engine: pdflatex
```

---

### 5. Compile the Generated LaTeX (via CV_BUILDER)

Take the `tex` and `engine` from the generate-cv response and send to CV_BUILDER:

```powershell
# Assuming $result has the generate-cv response
$compileBody = @{
    tex = $result.tex
    engine = $result.engine
    templateId = $result.template_id
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:3000/api/compile `
    -Method POST `
    -ContentType "application/json" `
    -Body $compileBody `
    -OutFile "resume.pdf"

# Open the PDF
Start-Process resume.pdf
```

```bash
# curl version
curl -X POST http://localhost:3000/api/compile \
  -H "Content-Type: application/json" \
  -d "{\"tex\": \"$(cat generated.tex)\", \"engine\": \"pdflatex\", \"templateId\": \"Jake_s_Resume__3_\"}" \
  --output resume.pdf
```

---

## Project Structure

```
LLM_BRAIN/
├── main.py                              # Slim entrypoint (FastAPI + CORS + router)
├── .env                                 # Environment variables
├── pyproject.toml                       # Python dependencies (uv)
│
└── app/
    ├── models.py                        # Pydantic models (UserProfile, RepoDetail, etc.)
    │
    ├── config/
    │   ├── __init__.py
    │   ├── serverConfig.py              # Env vars (PORT, GROQ_*, CV_BUILDER_URL)
    │   └── llmConfig.py                 # Groq LLM client factory
    │
    ├── prompts/
    │   ├── __init__.py
    │   ├── template_registry.py         # 8 templates → engine, macros, header, structure
    │   ├── system_prompt.py             # Template-aware prompt + completeness rules
    │   └── user_prompt.py               # User data + repo context builder
    │
    ├── service/
    │   ├── latex_generator_services.py  # Core orchestrator (fetch→prompt→LLM→validate→retry)
    │   ├── latex_sanitizer.py           # LaTeX post-processing & cleanup
    │   └── output_validator.py          # Completeness validation (sections, lines, structure)
    │
    └── routes/
        └── cv_routes.py                 # API endpoints (/health, /api/templates, /api/generate-cv)
```

---

## Supported Templates

| # | Template | Engine | Style |
|---|----------|--------|-------|
| 1 | **Jake's Resume** | `pdflatex` | Clean single-column, ATS-friendly |
| 2 | **AltaCV** | `lualatex` | Modern two-column with color accents |
| 3 | **Deedy CV** | `xelatex` | Compact two-column with custom fonts |
| 4 | **Awesome CV** | `xelatex` | Professional multi-section with color themes |
| 5 | **PlushCV** | `xelatex` | Modern two-column with icons |
| 6 | **ModernCV** | `pdflatex` | Classic professional with photo support |
| 7 | **Anubhav Resume** | `pdflatex` | Clean single-column, similar to Jake's |
| 8 | **dphang CV** | `pdflatex` | Simple article-based with FontAwesome icons |

---

## How It Prevents Half-Cooked Resumes

| Layer | What It Does |
|-------|-------------|
| **Prompt Hardening** | System prompt has explicit completeness rules: fill every section, 3-4 bullets per entry, fill full page, never truncate |
| **Output Validator** | Checks: has `\documentclass`? has `\end{document}`? user name present? all sections exist? 30+ content lines? has real bullet content? |
| **Retry with Feedback** | If validation fails, retries once telling the LLM exactly which checks failed |
| **Token Budget** | `GROQ_MAX_TOKENS=8192` (was 100 — literally couldn't fit a resume in 100 tokens) |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Failed to fetch template from CV_BUILDER` | Make sure CV_BUILDER is running on port 3000 |
| `Groq call failed` | Check `GROQ_API_KEY` in `.env`. Get a free key at [console.groq.com](https://console.groq.com) |
| Truncated output | Increase `GROQ_MAX_TOKENS` in `.env` (default: 8192) |
| `ModuleNotFoundError` | Run `uv sync` to install all dependencies |
| Wrong engine used | Check the `engine` field in the response — pass it to CV_BUILDER's compile endpoint |
