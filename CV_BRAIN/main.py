"""
LLM Brain — ATS Resume & LaTeX Generation Engine

Slim entrypoint: creates the FastAPI app, adds CORS, includes routes, and runs.
All business logic lives under app/ (models, prompts, services, routes).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes.cv_routes import router

app = FastAPI(title="LLM Brain - ATS Resume & LaTeX Generation Engine")

# /api/generate-cv spends real LLM credits on every call, so a wildcard origin
# lets any website on the internet drain the API key from a visitor's browser.
# Restrict to the known frontend; ALLOWED_ORIGINS overrides (comma-separated).
# Note: allow_origins=["*"] together with allow_credentials=True is also an
# invalid CORS combination that browsers reject outright.
_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
allowed_origins = (
    [o.strip() for o in _origins_env.split(",") if o.strip()]
    if _origins_env
    else [os.getenv("FRONTEND_URL", "http://localhost:5173")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    # reload=True spawns a file-watching supervisor — never in production.
    reload = os.getenv("ENV", "development").lower() != "production"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
