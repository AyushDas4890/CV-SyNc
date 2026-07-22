"""Diagnostic script: test the real LLM call end-to-end."""
import sys, os, asyncio
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env')

from app.service.latex_generator_services import call_llm, _has_valid_tex, strip_latex_comments
from app.prompts.system_prompt import build_system_prompt
from app.prompts.user_prompt import build_user_prompt
from app.models import UserProfile, EducationEntry, RepoDetail
import httpx

async def get_template():
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get('http://localhost:3000/api/templates/Resume_Template_by_Anubhav__2_/full')
        return resp.json().get('tex', '')

template_tex = asyncio.run(get_template())
clean_tex = strip_latex_comments(template_tex)

user_profile = UserProfile(
    name='Ayush Das',
    email='ayush@test.com',
    phone='9876543210',
    linkedin='linkedin.com/in/ayush',
    github='github.com/ayush',
    education=[EducationEntry(institution='Test University', degree='B.Tech CS', dates='2020-2024', gpa='8.5')],
    skills={}
)

repos = [RepoDetail(
    name='cv-sync',
    description='A CV synchronization tool',
    language='Python',
    topics=['python', 'fastapi'],
    url='https://github.com/ayush/cv-sync',
    readmeContent='# CV Sync\n\nFull stack CV builder using FastAPI and React. Generates LaTeX CVs using OpenAI.\n\n## Tech Stack\n- Backend: FastAPI, Python\n- Frontend: React, Vite\n- LLM: OpenAI GPT-4\n'
)]

user_prompt, has_exp, has_edu = build_user_prompt(user_profile, repos, clean_tex)
system_prompt = build_system_prompt('Resume_Template_by_Anubhav__2_', has_exp, has_edu, 1)

print(f"System prompt length: {len(system_prompt)}")
print(f"User prompt length: {len(user_prompt)}")

result = call_llm(system_prompt, user_prompt)

print(f"Result length: {len(result)}")
print(f"_has_valid_tex: {_has_valid_tex(result)}")
print(f"Has documentclass: {chr(92)}documentclass" in result)
print(f"Starts with backticks: {result.strip()[:10]!r}")
print()
print("=== FIRST 300 CHARS ===")
print(result[:300])
print()
print("=== LAST 100 CHARS ===")
print(result[-100:])
