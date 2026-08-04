# CV Builder - LaTeX Compilation Microservice

A scalable, containerized Node.js microservice designed to compile raw LaTeX source code (`.tex`) into PDF documents (`.pdf`) securely on the fly. It natively supports advanced resume templates (like Awesome CV and Deedy CV) and provides AI-ready endpoints for automated CV generation.

## 🏗️ Architecture

The application is structured using a robust **Model-View-Controller (MVC) / Service-Oriented Architecture** to enforce a clean separation of concerns.

```text
src/
├── config/
│   └── server.config.js       # Environment configuration and PORT settings
├── controller/
│   ├── latex.controller.js    # Handles compilation HTTP requests and dynamic compiler inference
│   └── template.controller.js # Exposes CV templates and handles sub-file concatenation for LLMs
├── router/
│   ├── latex.router.js        # Maps compilation API routes
│   └── template.router.js     # Maps template discovery API routes
├── service/
│   └── latex.service.js       # Core logic: isolated workspaces, fs operations, child processes
├── templates/                 # Pre-configured premium CV templates (Awesome CV, Deedy, etc.)
└── index.js                   # Application entry point: wires up Express, CORS, and routers
```

### 1. Controllers
Acts as the middleman. 
* `LatexController` intercepts incoming compilation requests, validates the `tex` payload, automatically infers the correct LaTeX engine (`xelatex`, `pdflatex`, etc.) based on the template, and formats the success/failure response back to the client.
* `TemplateController` serves available templates to the frontend/LLM. Crucially, it provides a `/full` endpoint that parses LaTeX `\input{}` macros and inlines sub-files to provide a single, comprehensive string for AI manipulation.

### 2. Services (`latex.service.js`)
Handles the actual business logic. It generates a unique `jobID`, creates an isolated temporary directory in the OS, copies required template assets (fonts, classes), writes the LaTeX string to `doc.tex`, and spawns a secure LaTeX compiler child process. It forcefully cleans up the temporary directory upon completion to prevent memory leaks.

---

## 🔄 End-to-End Flow

1. **AI / Client Request**: The client requests a master template string via `GET /api/templates/:id/full`. The backend recursively inlines all `\input{}` dependencies into one string.
2. **AI Modification**: The LLM edits the text content inside the master string and sends it back via `POST /api/compile`.
3. **Service Execution**:
   - `LatexService` creates a temporary directory `/tmp/latex-jobs/<UUID>/`.
   - The required assets from `src/templates/<templateId>` (like fonts, `.cls` files) are securely copied into the temporary job workspace.
   - A Node.js `child_process` spawns the correct engine with strict security flags (`-interaction=nonstopmode`, `-no-shell-escape`, `-halt-on-error`).
4. **Compilation Result**:
   - **Success**: The service reads `doc.pdf` into a Buffer and returns it. The Controller sends it back to the client with a `Content-Type: application/pdf` header.
   - **Failure**: The service extracts the raw `.log` file and parses human-readable errors using Regex, returning a `422 Unprocessable Entity` JSON response for the LLM to auto-correct.
5. **Cleanup**: Regardless of success or failure, the service forcefully deletes the temporary directory.

---

## 🐳 Docker Deployment

The application is heavily containerized using a TeX Live image (`minidocks/texlive:2023-medium`). The `Dockerfile` has been heavily customized to pre-install dependencies (`fontawesome5`, `fontconfig`, `tikzfill`, etc.) required by complex templates.

### Build the Image

```bash
docker build -t cv-builder-service .
```

### Run the Container

```bash
docker run -p 3000:3000 cv-builder-service
```

---

## 🚀 API Reference

### 1. Health Check
**Endpoint**: `GET /api/health`
**Response**: `200 OK`
```json
{ "ok": true }
```

---

### 2. List Templates
**Endpoint**: `GET /api/templates`
Returns a list of all available template IDs installed in the system.
**Response**: `200 OK`
```json
{
  "success": true,
  "templates": ["Awesome_CV__3_", "Deedy_CV__1_", "Jake_s_Resume"]
}
```

---

### 3. Get AI-Ready Template (Concatenated)
**Endpoint**: `GET /api/templates/:id/full`
Returns a single, massive LaTeX string with all `\input{...}` macros resolved and injected. **Perfect for LLM context windows.**
**Response**: `200 OK`
```json
{
  "success": true,
  "templateId": "Awesome_CV__3_",
  "tex": "\\documentclass{awesome-cv} ... [all inputs resolved inline] ... \\end{document}"
}
```

---

### 4. Compile LaTeX
**Endpoint**: `POST /api/compile`
**Headers**: `Content-Type: application/json`

**Body**:
```json
{
  "templateId": "Awesome_CV__3_",
  "tex": "\\documentclass{awesome-cv}...\\end{document}"
}
```

**Success Response (200 OK)**:
Returns raw binary `application/pdf` data.

**Error Response (422 Unprocessable Entity)**:
```json
{
  "ok": false,
  "log": "... raw LaTeX log output ...",
  "errors": [
    {
      "file": "./awesome-cv.cls",
      "line": 166,
      "message": "LaTeX cmd Error: Command '\\FA' already defined."
    }
  ]
}
```
