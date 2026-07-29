"""
Pydantic models for LLM_BRAIN API requests and responses.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Kept in sync with page_metrics.ALLOWED_LENGTHS. Declared here rather than
# imported to avoid models.py depending on the service layer.
ALLOWED_PAGE_TARGETS = {1.0, 1.5, 2.0}


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
    # Accept either the alias (full_name, readme_content, ...) or the field
    # name (fullName, readmeContent). Without this, a caller sending camelCase
    # gets the field silently dropped to its default instead of an error.
    model_config = ConfigDict(populate_by_name=True)

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
    # Document length target. "auto" (default) lets the content decide, then
    # snaps to whichever of 1 / 1.5 / 2 pages it lands nearest. A number pins
    # it to that exact band. Only 1, 1.5 and 2 are valid — see
    # page_metrics.ALLOWED_LENGTHS.
    target_pages: Optional[Union[float, str]] = "auto"
    # Backward compat: if provided, skip fetching from CV_BUILDER
    latex_template: Optional[str] = None

    @field_validator("target_pages")
    @classmethod
    def _validate_target_pages(cls, v):
        if v is None:
            return "auto"
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("", "auto"):
                return "auto"
            try:
                v = float(s)
            except ValueError:
                raise ValueError("target_pages must be 'auto', 1, 1.5 or 2")
        v = float(v)
        if v not in ALLOWED_PAGE_TARGETS:
            raise ValueError(
                f"target_pages must be 'auto' or one of {sorted(ALLOWED_PAGE_TARGETS)}, got {v}"
            )
        return v


# ── Validation Result Model ──────────────────────────────────────────────────

class ValidationResult(BaseModel):
    passed: bool = False
    failures: List[str] = []
    checks: Dict[str, bool] = {}
