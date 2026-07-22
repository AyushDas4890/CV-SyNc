"""
Pydantic models for LLM_BRAIN API requests and responses.
"""
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── User Profile Models ──────────────────────────────────────────────────────

class EducationEntry(BaseModel):
    institution: Optional[str] = ""
    degree: Optional[str] = ""
    location: Optional[str] = ""
    dates: Optional[str] = ""
    gpa: Optional[str] = ""


class ExperienceEntry(BaseModel):
    company: Optional[str] = ""
    role: Optional[str] = ""
    location: Optional[str] = ""
    dates: Optional[str] = ""
    bullets: Optional[Any] = ""


class AchievementEntry(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    date: Optional[str] = ""


class UserProfile(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    portfolio: Optional[str] = ""
    summary: Optional[str] = ""
    education: Optional[List[EducationEntry]] = []
    experience: Optional[List[ExperienceEntry]] = []
    achievements: Optional[List[AchievementEntry]] = []
    skills: Optional[Dict[str, Any]] = {}
    certifications: Optional[List[Any]] = []


# ── Repository Detail Model ──────────────────────────────────────────────────

class RepoDetail(BaseModel):
    id: Optional[Any] = None
    name: Optional[str] = ""
    fullName: Optional[str] = Field(default="", alias="full_name")
    description: Optional[str] = ""
    language: Optional[str] = ""
    stars: Optional[int] = 0
    topics: Optional[List[str]] = []
    url: Optional[str] = ""
    readmeContent: Optional[str] = Field(default="", alias="readme_content")
    manifests: Optional[Dict[str, str]] = {}
    fileTreeSample: Optional[List[str]] = Field(default=[], alias="file_tree_sample")
    topFileHeaders: Optional[Dict[str, str]] = Field(default={}, alias="top_file_headers")
    commitMessages: Optional[List[str]] = Field(default=[], alias="commit_messages")
    userNotes: Optional[str] = Field(default="", alias="user_notes")


# ── API Request Model ────────────────────────────────────────────────────────

class GenerateCvRequest(BaseModel):
    user_profile: UserProfile
    selected_repos: List[RepoDetail] = []
    template_id: Optional[str] = "Jake_s_Resume__3_"
    target_role: Optional[str] = ""
    target_pages: Optional[int] = 1
    # Backward compat: if provided, skip fetching from CV_BUILDER
    latex_template: Optional[str] = None


# ── Validation Result Model ──────────────────────────────────────────────────

class ValidationResult(BaseModel):
    passed: bool = False
    failures: List[str] = []
    checks: Dict[str, bool] = {}
