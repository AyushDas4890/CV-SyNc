from dotenv import load_dotenv
load_dotenv()

import os

PORT = os.getenv("PORT", "8000")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = os.getenv("GROQ_TEMPERATURE", "0.1")
GROQ_MAX_TOKENS = os.getenv("GROQ_MAX_TOKENS", "8192")
CV_BUILDER_URL = os.getenv("CV_BUILDER_URL", "http://localhost:3000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Refinement passes ────────────────────────────────────────────────────────
# Each of these costs an extra LLM call (and, for page fitting, a compile), so
# they are individually switchable and bounded.

# LLM audit of the generated tex against the template's structure.
ENABLE_STRUCTURE_REVIEW = os.getenv("ENABLE_STRUCTURE_REVIEW", "true").lower() == "true"

# Compile → measure → expand/condense loop to hit a 1 / 1.5 / 2 page target.
ENABLE_PAGE_FIT = os.getenv("ENABLE_PAGE_FIT", "true").lower() == "true"

# Max expand/condense rounds. Each round = 1 LLM call + 1 compile.
PAGE_FIT_MAX_ATTEMPTS = int(os.getenv("PAGE_FIT_MAX_ATTEMPTS", "3"))

# Seconds to wait on a measurement compile before giving up on page fitting.
PAGE_FIT_COMPILE_TIMEOUT = float(os.getenv("PAGE_FIT_COMPILE_TIMEOUT", "120"))

def Server_Credentials()->dict:
    return {
        "PORT": PORT,
        "GROQ_API_KEY": GROQ_API_KEY,
        "GROQ_MODEL": GROQ_MODEL,
        "GROQ_TEMPERATURE": GROQ_TEMPERATURE,
        "GROQ_MAX_TOKENS": GROQ_MAX_TOKENS,
        "CV_BUILDER_URL": CV_BUILDER_URL,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "ENABLE_STRUCTURE_REVIEW": ENABLE_STRUCTURE_REVIEW,
        "ENABLE_PAGE_FIT": ENABLE_PAGE_FIT,
        "PAGE_FIT_MAX_ATTEMPTS": PAGE_FIT_MAX_ATTEMPTS,
        "PAGE_FIT_COMPILE_TIMEOUT": PAGE_FIT_COMPILE_TIMEOUT,
    }
