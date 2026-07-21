# CV-Sync 🚀

**Automated LaTeX Resume Synchronization from GitHub Repositories**

CV-Sync automatically keeps the *Projects & Work Experience* sections of your resume seamlessly synchronized with your active GitHub repositories. It fetches repository metadata, leverages AI to distill clean, metric-driven action bullets, injects them into standard LaTeX resume templates (e.g., Jake Gutierrez template), and compiles pixel-perfect PDF resumes with human-in-the-loop approval.

---

## 🎨 Visual System & Design Philosophy

Built with a **Deep Sapphire Blue `#0A192F` & Warm Gold `#F59E0B`** premium aesthetic, CV-Sync brings state-of-the-art visual polish and responsive user experience across both web interfaces and generated LaTeX artifacts.

---

## 🏗 System Architecture

CV-Sync is structured as a decoupled microservices architecture designed for reliability, strict type safety, and deterministic rendering.

```
┌─────────────────┐       ┌───────────────────────┐       ┌──────────────────────┐
│  React / Vite   │ ────> │ Auth Service          │ ────> │ Fetch & LLM Engine   │
│  Frontend App   │       │ (Express + GitHub OAuth)│      │ (GitHub API + RAG)   │
└─────────────────┘       └───────────────────────┘       └──────────┬───────────┘
                                                                     │
                                                                     ▼ `projects.json` (Contract)
┌─────────────────┐       ┌───────────────────────┐       ┌──────────────────────┐
│ PDF Output      │ <──── │ Compiler Service      │ <──── │ Writer Service       │
│ (Download/Diff) │       │ (LaTeX Engine + Tectonic)│      │ (LaTeX Injector + Diff)│
└─────────────────┘       └───────────────────────┘       └──────────────────────┘
```

---

## 🛠 Key Features

* **Deterministic LaTeX Pipeline**: Never relies on LLMs to write raw LaTeX code. The LLM produces strict JSON, while a deterministic renderer safely injects contents into master `.tex` templates.
* **Human-in-the-Loop Diff Approval Gate**: Inspect side-by-side colorized diffs of your resume changes before compiling the final PDF artifact.
* **GitHub OAuth & Repository Tagging**: Authenticate via GitHub and selectively select which repositories and performance metrics (`notes`) belong on your resume.
* **Microservices Ready**: Decoupled Express.js backend services and React (Vite) frontend designed to run via Docker Compose.

---

## 📦 Project Structure

```
CV SYNC/
├── backend/
│   └── auth-service/           # Express.js GitHub OAuth & Session Manager
│       ├── src/
│       │   ├── controllers/    # GitHub Auth logic
│       │   ├── middleware/     # Session validation
│       │   ├── routes/         # OAuth endpoints (/auth/github, /auth/user)
│       │   └── services/       # User store & token management
│       ├── .env.example
│       └── package.json
├── frontend/                   # Modern React + Vite Web Application
│   ├── src/
│   │   ├── components/         # Reusable UI components & Logout bar
│   │   ├── pages/              # Auth, GitHub Connect, Experience, Templates
│   │   ├── api.js              # Centralized Axios client
│   │   └── styles.css          # Blue & Gold design system tokens
│   ├── index.html
│   └── package.json
├── kb/                         # Project Architecture Knowledge Base
│   ├── 00-project.md           # Project state & team ownership
│   ├── 01-architecture.md      # Microservice communication flow
│   ├── 02-auth-service.md      # Auth Service specs
│   ├── 03-compiler-service.md  # LaTeX compilation specs
│   ├── 04-writer-service.md    # Resume Writer specs
│   ├── 05-llm-rag.md           # LLM RAG & bullet generation design
│   ├── 06-build-plan.md        # Engineering roadmap & milestones
│   └── INDEX.md
└── .gitignore                  # Global repository ignores (Secrets, Build artifacts)
```

---

## ⚙️ Service Specifications & API Contracts

### 1. Auth Service (`backend/auth-service`)
Runs on port `3001` (by default) and manages GitHub OAuth flows.

* `GET /auth/github`: Initiates GitHub OAuth authentication flow.
* `GET /auth/github/callback`: Handles GitHub authorization code exchange.
* `GET /auth/user`: Returns current authenticated session.
* `POST /auth/logout`: Clears session cookie.

### 2. The Data Contract (`projects.json`)
The immutable contract passed between the Fetch/LLM engine and the Writer Service:

```json
[
  {
    "title": "Legal Clause Conflict Resolver",
    "tech_stack": ["Python", "DeBERTa-v3", "FAISS", "FastAPI"],
    "bullets": [
      "Fine-tuned DeBERTa-v3-large on NLI dataset achieving >87% validation accuracy.",
      "Optimized vector search pipeline using FAISS to reduce query latency by 45%."
    ],
    "repo_url": "https://github.com/AyushDas4890/Legal-Conflict-Resolver",
    "dates": "Jan 2026 – Present"
  }
]
```

### 3. Compiler Service API Contract
Compiler service accepts raw LaTeX string payloads and converts them to binary PDF or structured error logs:

* `POST /api/compile`
  * **Payload**: `{ "tex": "..." }`
  * **Response 200**: Binary `application/pdf` stream
  * **Response 422**: `{ "ok": false, "log": "...", "errors": [{ "file": "...", "line": 42, "message": "..." }] }`

---

## 🚀 Quickstart & Local Setup

### Prerequisites
* **Node.js**: v18.x or higher
* **npm**: v9.x or higher
* **GitHub OAuth App**: Registered in GitHub Developer Settings (Callback: `http://localhost:3001/auth/github/callback`)

### 1. Backend Auth Service
```bash
cd backend/auth-service
cp .env.example .env
# Fill in GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, and SESSION_SECRET in .env
npm install
npm run dev
```

### 2. Frontend Development Server
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

---

## 🛡️ Security Guidelines

* `.env` files, build output (`dist/`), and `node_modules/` are strictly excluded from version control via root `.gitignore`.
* Secrets and API tokens must never be committed to repository history.

---

*Crafted for peak developer impact & resume synchronization.* ⚡
