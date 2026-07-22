"""
User prompt builder — constructs the user data + repo context + template tex
prompt that gets sent alongside the system prompt to the LLM.
"""

import json
import re
from typing import List

from app.models import UserProfile, RepoDetail


def _escape_latex(text: str) -> str:
    """Sanitize and escape special LaTeX characters in plain text strings."""
    if not isinstance(text, str):
        return text
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
    }
    pattern = re.compile(r'(?<!\\)([&%$#_])')
    return pattern.sub(lambda m: chars.get(m.group(1), m.group(1)), text)


def _build_repo_context(repos: List[RepoDetail]) -> str:
    """Build rich context blocks from selected GitHub repositories."""
    if not repos:
        return "No GitHub repositories selected."

    repo_facts = []
    for r in repos:
        name = _escape_latex(r.name or r.fullName)
        desc = _escape_latex(r.description or "No description provided.")
        lang = _escape_latex(r.language or "Unknown")
        topics = _escape_latex(", ".join(r.topics)) if r.topics else "None"
        clean_url = r.url or ""

        fact_block = (
            f"### Repository: {name}\n"
            f"- URL: {clean_url}\n"
            f"- Primary Language: {lang}\n"
            f"- Topics: {topics}\n"
            f"- Description: {desc}\n"
        )

        if r.userNotes:
            fact_block += f"- User Performance Notes: {_escape_latex(r.userNotes)}\n"

        if r.readmeContent:
            snippet = r.readmeContent[:800]
            fact_block += f"- README Excerpt:\n```\n{snippet}\n```\n"
        else:
            fact_block += "- README: NONE (NO README FILE IN REPO)\n"
            if r.manifests:
                fact_block += "- Extracted Package Manifests (Dependencies & Scripts):\n"
                for m_name, m_content in r.manifests.items():
                    fact_block += f"  * File `{m_name}`:\n```\n{m_content[:1000]}\n```\n"
            if r.commitMessages:
                fact_block += f"- Recent Commit History: {'; '.join(r.commitMessages[:6])}\n"
            if r.topFileHeaders:
                fact_block += "- Entry Point Code Snippets:\n"
                for f_name, f_head in r.topFileHeaders.items():
                    fact_block += f"  * File `{f_name}`:\n```\n{f_head[:500]}\n```\n"
            if r.fileTreeSample:
                fact_block += f"- Sample File Tree: {', '.join(r.fileTreeSample[:20])}\n"

        repo_facts.append(fact_block)

    return "\n".join(repo_facts)


def _build_user_info(user: UserProfile) -> tuple:
    """
    Build the user info string and determine data availability flags.
    Returns (user_info_str, has_experience, has_education).
    """
    user_name = _escape_latex(user.name or "")
    user_email = _escape_latex(user.email or "")
    user_phone = _escape_latex(user.phone or "")
    user_location = _escape_latex(user.location or "")
    user_linkedin = _escape_latex(user.linkedin or "")
    user_github = _escape_latex(user.github or "")
    user_summary = _escape_latex(user.summary or "")

    has_experience = bool(
        user.experience
        and len([e for e in user.experience if e.company or e.role]) > 0
    )
    has_education = bool(
        user.education
        and len([e for e in user.education if e.institution or e.degree]) > 0
    )

    user_info_str = f"""
Name: {user_name}
Email: {user_email}
Phone: {user_phone}
Location: {user_location}
LinkedIn: {user_linkedin}
GitHub: {user_github}
Portfolio: {user.portfolio}
Summary / Bio: {user_summary}

Education Provided: {has_education}
Education:
{json.dumps([e.dict() for e in user.education], indent=2) if user.education else "NONE (User provided no education)."}

Certifications:
{json.dumps(user.certifications, indent=2) if user.certifications else "None provided."}

Achievements & Honors:
{json.dumps([a.dict() for a in user.achievements], indent=2) if user.achievements else "None provided."}

Work Experience Provided: {has_experience}
Experience Entries:
{json.dumps([e.dict() for e in user.experience], indent=2) if user.experience else "NONE (User provided no work experience)."}

Skills & Technologies:
{json.dumps(user.skills, indent=2) if user.skills else "Infer technical skills from projects and user input."}
"""
    return user_info_str, has_experience, has_education


def build_user_prompt(
    user: UserProfile,
    repos: List[RepoDetail],
    template_tex: str,
) -> tuple:
    """
    Build the complete user prompt for the LLM.
    
    Returns:
        (user_prompt_str, has_experience, has_education)
    """
    user_info_str, has_experience, has_education = _build_user_info(user)
    repo_context_str = _build_repo_context(repos)

    mapping_instructions = f"""REQUIRED SUBSTITUTIONS:
- Replace the name placeholder (e.g., "Jake Ryan", "Sourabh Bajaj", etc.) with the user's name: "{user.name}"
- Replace the contact info placeholders (phone, email, linkedin, github, portfolio) with the user's info:
    - Email: "{user.email}"
    - Phone: "{user.phone}"
    - Location: "{user.location}"
    - LinkedIn: "{user.linkedin}"
    - GitHub: "{user.github}"
    - Portfolio: "{user.portfolio}"
- Replace ALL education entries with the user's actual education entries listed under CANDIDATE DATA.
- Replace ALL work experience/employment entries with the user's actual work experience listed under CANDIDATE DATA.
- Replace ALL project/repository entries with the user's actual projects listed under GITHUB REPOSITORIES.
- Replace ALL skills/languages/frameworks with the user's actual skills listed under CANDIDATE DATA.
- If the template has (or can accommodate) an Achievements/Honors/Awards section and the user provided any, include them — do not drop them silently.
"""

    user_prompt = f"""CRITICAL INSTRUCTION:
The template below contains SAMPLE DATA (e.g. "Jake Ryan", "Southwestern University", "Gitlytics", etc.).
You MUST replace ALL sample data with the real CANDIDATE DATA provided below.
Do NOT output the sample data or placeholders in the final document.

{mapping_instructions}

=========================================
CANDIDATE DATA:
=========================================
{user_info_str}

=========================================
GITHUB REPOSITORIES:
=========================================
{repo_context_str}

=========================================
TEMPLATE TO FILL (Replace ALL sample data, preserve structure):
=========================================
{template_tex}

=========================================
INSTRUCTIONS FOR FINAL OUTPUT:
=========================================
Fill in the template with the candidate's data now.
- Every single section must contain real candidate data.
- Replace every placeholder name, institution, job title, project name, bullet point, and tech skill.
- Return the COMPLETE LaTeX document from \\documentclass to \\end{{document}}.
- Do NOT truncate or cut off the output. Do NOT include markdown code fences (```) or conversational response text.
"""

    return user_prompt, has_experience, has_education
