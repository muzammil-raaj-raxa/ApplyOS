import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import ROOT_DIR

SEARCH_PROFILE_PATH = ROOT_DIR / "data" / "search_profile.json"
KNOWN_SOURCES = ("greenhouse", "lever", "ashby")
SLUG = re.compile(r"^[A-Za-z0-9_.-]+$")


class SearchProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    minimum_score: int = Field(default=80, ge=0, le=100)
    exclude_keywords: list[str] = Field(default_factory=list)
    # company slugs per source, e.g. {"greenhouse": ["stripe"], "ashby": ["ramp"]}
    companies: dict[str, list[str]] = Field(default_factory=dict)
    # optional display names, e.g. {"openai": "OpenAI"}
    company_names: dict[str, str] = Field(default_factory=dict)

    @field_validator("companies")
    @classmethod
    def check_companies(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for source, slugs in value.items():
            if source not in KNOWN_SOURCES:
                raise ValueError(f"unknown source '{source}' (use: {', '.join(KNOWN_SOURCES)})")
            for slug in slugs:
                if not SLUG.match(slug):
                    raise ValueError(f"'{slug}' is not a valid company slug")
        return value


def default_search_profile() -> SearchProfile:
    return SearchProfile(
        target_roles=["iOS Engineer", "iOS Developer", "Mobile Engineer", "Swift Developer"],
        locations=["Remote", "Pakistan", "Worldwide"],
        employment_types=["Full-time"],
        minimum_score=80,
        exclude_keywords=["Senior Staff", "Principal"],
        # Starting points only. A wrong slug just shows up as a 'not found' error.
        companies={
            "greenhouse": ["stripe", "airbnb", "figma", "databricks"],
            "lever": ["spotify", "palantir"],
            "ashby": ["ramp", "notion", "linear", "openai"],
        },
    )


def load_search_profile(path: Path | None = None) -> SearchProfile:
    path = path or SEARCH_PROFILE_PATH
    if not path.exists():
        return default_search_profile()
    return SearchProfile.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_search_profile(profile: SearchProfile, path: Path | None = None) -> None:
    path = path or SEARCH_PROFILE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")
