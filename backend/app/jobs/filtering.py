import re
from dataclasses import dataclass, field

from app.jobs.deduplication import title_key
from app.jobs.schemas import NormalizedJob
from app.jobs.search_profile import SearchProfile
from app.profile.validator import Preferences

SENIORITY_GAP_YEARS = 4  # reject when a job asks for this many more years than the profile has

PRIMARY_ROLE = re.compile(r"\b(ios|swift|swiftui|iphone|mobile)\b")
SECONDARY_ROLE = re.compile(
    r"\b(software (?:engineer|developer)|front ?end|application developer|app developer)\b"
)
CROSS_PLATFORM = re.compile(r"\b(ios|swift|iphone|cross platform|react native|flutter)\b")
TOO_SENIOR = re.compile(
    r"\b(staff|principal|distinguished|director|vp|vice president|head of|chief|fellow)\b"
)

_REGION = (
    r"(?:the )?(?:us|u\.s\.|usa|united states|canada|uk|united kingdom|eu|"
    r"european union|europe|australia)"
)
_REMOTE_REGION_LOCATION = [
    re.compile(rf"^\s*remote\s*[\-–—,:(|/]*\s*\(?\s*{_REGION}\b", re.IGNORECASE),
    re.compile(rf"\b{_REGION}\s*[\-–—(]?\s*remote\b", re.IGNORECASE),
]
_REGION_IN_TEXT = [
    re.compile(rf"\bmust (?:be )?(?:located|based|reside|live|living|resident)s? in {_REGION}\b", re.IGNORECASE),
    re.compile(rf"\b{_REGION}[- ]only\b", re.IGNORECASE),
    re.compile(rf"\bonly (?:considering|accepting|hiring)(?: candidates| applicants)?(?: (?:from|in|located in)) {_REGION}\b", re.IGNORECASE),
]
_CLOSED = re.compile(
    r"no longer accepting applications|position has been filled|this (?:job|position|role|posting) (?:is|has been) (?:closed|filled|expired)|"
    r"posting has expired|applications are closed",
    re.IGNORECASE,
)
_EMPLOYMENT_ALIASES = {
    "full-time": "full-time", "fulltime": "full-time", "full time": "full-time",
    "part-time": "part-time", "parttime": "part-time", "part time": "part-time",
    "contract": "contract", "internship": "internship", "intern": "internship",
}


@dataclass
class FilterResult:
    passed: bool
    role_tier: str  # primary | secondary | unrelated
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"passed": self.passed, "role_tier": self.role_tier, "reasons": self.reasons}


def role_tier(title: str) -> str:
    key = title_key(title)
    if PRIMARY_ROLE.search(key):
        return "primary"
    if SECONDARY_ROLE.search(key):
        return "secondary"
    return "unrelated"


def filter_job(
    job: NormalizedJob,
    search: SearchProfile,
    prefs: Preferences | None = None,
    candidate_years: float | None = None,
) -> FilterResult:
    """Deterministic checks that run before any AI call. Each match is its own reason.
    A missing preferred skill is never a reason."""
    reasons: list[str] = []
    tier = role_tier(job.title)
    lowered = job.title.lower()  # raw title: bracketed words like "(Android)" still count

    if tier == "unrelated":
        reasons.append("unrelated role")
    if re.search(r"\bandroid\b", lowered) and not CROSS_PLATFORM.search(lowered):
        reasons.append("Android-only role")

    for keyword in search.exclude_keywords:
        if keyword.strip() and keyword.lower() in job.title.lower():
            reasons.append(f"title contains excluded keyword '{keyword}'")
    senior = TOO_SENIOR.search(lowered)
    if senior:
        reasons.append(f"seniority too high ('{senior.group(1)}' level)")
    years = job.requirements.get("minimum_years")
    if years is not None and candidate_years is not None:
        if years >= candidate_years + SENIORITY_GAP_YEARS:
            reasons.append(f"asks for {years}+ years; profile has about {candidate_years:.0f}")

    if prefs is not None:
        if job.workplace == "onsite" and not prefs.onsite:
            reasons.append("onsite roles are turned off in your preferences")
        if job.workplace == "hybrid" and not prefs.hybrid:
            reasons.append("hybrid roles are turned off in your preferences")
        if job.workplace == "remote" and not prefs.remote:
            reasons.append("remote roles are turned off in your preferences")

    if job.workplace == "remote":
        region = _remote_region(job)
        if region:
            reasons.append(f"remote role limited to {region}")

    if _CLOSED.search(job.description):
        reasons.append("application appears to be closed")

    allowed = {
        _EMPLOYMENT_ALIASES.get(t.strip().lower(), t.strip().lower()) for t in search.employment_types
    }
    if allowed and job.employment_type and job.employment_type not in allowed:
        reasons.append(f"employment type '{job.employment_type}' is not in your search profile")

    return FilterResult(passed=not reasons, role_tier=tier, reasons=reasons)


def _remote_region(job: NormalizedJob) -> str | None:
    location = job.location or ""
    for pattern in _REMOTE_REGION_LOCATION:
        match = pattern.search(location)
        if match:
            return match.group(0).strip(" -–—,:(|/").lower().replace("remote", "").strip(" -–—,:(|/") or "one region"
    for pattern in _REGION_IN_TEXT:
        match = pattern.search(job.description)
        if match:
            return "a region that excludes you ('" + " ".join(match.group(0).split()) + "')"
    return None
