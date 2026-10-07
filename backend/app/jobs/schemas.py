from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


@dataclass
class RawJob:
    """What a source adapter returns: close to the source's own data, not yet cleaned."""

    source: str
    external_id: str | None
    title: str
    company: str
    url: str
    description: str = ""  # may contain HTML
    location: str | None = None
    posted_date: datetime | None = None
    workplace_hint: str | None = None  # "remote", "hybrid", "on-site" when the source says so
    employment_hint: str | None = None  # e.g. "FullTime", "Full-time"
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None


class NormalizedJob(BaseModel):
    title: str
    company: str
    location: str | None
    remote: bool | None
    workplace: str  # remote | hybrid | onsite | unknown
    url: str
    description: str
    source: str
    external_id: str | None
    posted_date: datetime | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    employment_type: str | None
    requirements: dict
    company_key: str
    title_key: str
    location_key: str
    fingerprint: str
    parsing_error: str | None
