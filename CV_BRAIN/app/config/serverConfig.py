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

def Server_Credentials()->dict:
    return {
        "PORT": PORT,
        "GROQ_API_KEY": GROQ_API_KEY,
        "GROQ_MODEL": GROQ_MODEL,
        "GROQ_TEMPERATURE": GROQ_TEMPERATURE,
        "GROQ_MAX_TOKENS": GROQ_MAX_TOKENS,
        "CV_BUILDER_URL": CV_BUILDER_URL,
        "OPENAI_API_KEY": OPENAI_API_KEY,
    }
