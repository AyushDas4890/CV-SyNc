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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
