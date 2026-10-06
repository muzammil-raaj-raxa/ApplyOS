import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROFILE_PATH = Path(__file__).resolve().parent / "career_profile.json"

YEAR_MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"  # e.g. 2025-03

EvidenceSource = Literal[
    "professional_work",
    "project",
    "certification",
    "education",
    "profile_link",
    "user_confirmed",  # the user explicitly confirmed it; counts as evidence
    "self_reported",  # listed only, nothing backs it up yet; does NOT count
]


class Strict(BaseModel):
    """Base class: unknown fields are errors, so typos in the JSON are caught."""

    model_config = ConfigDict(extra="forbid")


class Evidence(Strict):
    source: EvidenceSource
    description: str = Field(min_length=1)


class Skill(Strict):
    name: str = Field(min_length=1)
    category: str
    status: Literal["confirmed", "needs_evidence"]
    evidence: list[Evidence] = []
    note: str | None = None

    @model_validator(mode="after")
    def confirmed_skill_needs_real_evidence(self):
        if self.status == "confirmed":
            real = [e for e in self.evidence if e.source != "self_reported"]
            if not real:
                raise ValueError(f"skill '{self.name}' is 'confirmed' but has no real evidence")
        return self


class Bullet(Strict):
    id: str
    text: str = Field(min_length=1)
    status: Literal["confirmed", "needs_confirmation"] = "confirmed"
    note: str | None = None  # why it needs confirmation
    safe_text: str | None = None  # the bullet without the unconfirmed claim
    skills: list[str] = []  # names that must exist in the skills list

    @model_validator(mode="after")
    def flagged_bullet_needs_a_note(self):
        if self.status == "needs_confirmation" and not self.note:
            raise ValueError(f"bullet '{self.id}' needs_confirmation but has no note")
        return self

    def usable_text(self) -> str | None:
        """Text the resume generator may use. None means: do not use this bullet yet."""
        if self.status == "confirmed":
            return self.text
        return self.safe_text


class Experience(Strict):
    id: str
    title: str
    company: str
    location: str | None = None
    start: str = Field(pattern=YEAR_MONTH)
    end: str | None = Field(default=None, pattern=YEAR_MONTH)  # None = present
    bullets: list[Bullet] = []


class Project(Strict):
    id: str
    name: str
    description: str
    technologies: list[str] = []
    url: str | None = None
    bullets: list[Bullet] = []


class Education(Strict):
    degree: str
    institution: str
    location: str | None = None
    start: str = Field(pattern=YEAR_MONTH)
    end: str | None = Field(default=None, pattern=YEAR_MONTH)


class Certification(Strict):
    name: str
    issuer: str
    date: str = Field(pattern=YEAR_MONTH)


class TargetRole(Strict):
    title: str
    tier: Literal["primary", "secondary"]


class Candidate(Strict):
    name: str
    location: str
    email: str
    phone: str
    linkedin: str
    github: str
    portfolio: str


class Preferences(Strict):
    remote: bool
    hybrid: bool
    onsite: bool
    relocation: bool


class CareerProfile(Strict):
    profile_version: str
    candidate: Candidate
    target_roles: list[TargetRole]
    experience: list[Experience]
    education: list[Education]
    skills: list[Skill]
    projects: list[Project]
    achievements: list[dict] = []
    certifications: list[Certification]
    work_authorization: dict = {}
    preferences: Preferences
    salary_preferences: dict = {}
    evidence: list[dict] = []

    @model_validator(mode="after")
    def tags_must_reference_real_skills(self):
        known = {s.name.lower() for s in self.skills}
        if len(known) != len(self.skills):
            raise ValueError("duplicate skill names in profile")
        for job in self.experience:
            for bullet in job.bullets:
                for tag in bullet.skills:
                    if tag.lower() not in known:
                        raise ValueError(f"{job.company} bullet '{bullet.id}': unknown skill '{tag}'")
        for project in self.projects:
            for tech in project.technologies:
                if tech.lower() not in known:
                    raise ValueError(f"project '{project.name}': unknown technology '{tech}'")
            for bullet in project.bullets:
                for tag in bullet.skills:
                    if tag.lower() not in known:
                        raise ValueError(f"project '{project.name}' bullet '{bullet.id}': unknown skill '{tag}'")
        return self


def load_profile(path: Path | None = None) -> CareerProfile:
    """Read and validate the career profile. Raises if the file is missing or invalid."""
    path = path or PROFILE_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return CareerProfile.model_validate(data)
