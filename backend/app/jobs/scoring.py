"""Deterministic scoring pieces. No AI and no database in this file."""
import re

from app.profile.validator import Preferences

# Spec section 14: the weights add up to 100.
WEIGHTS = {
    "technical": 30,
    "experience": 20,
    "seniority": 15,
    "location": 10,
    "authorization": 10,
    "role": 10,
    "domain": 5,
}
assert sum(WEIGHTS.values()) == 100

PAKISTAN_HINTS = ("pakistan", "islamabad", "rawalpindi", "lahore", "karachi", "peshawar", "faisalabad")
PLATFORM_ALIASES = {"ios": {"swift", "swiftui", "uikit"}}


def overall_score(scores: dict[str, int]) -> int:
    total = sum(WEIGHTS[name] * scores[name] for name in WEIGHTS)
    return (total + 50) // 100  # round half up, integers only


def band(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Strong"
    if score >= 70:
        return "Review"
    if score >= 60:
        return "Low priority"
    return "Reject"


def priority(score: int) -> str:
    if score >= 95:
        return "CRITICAL"
    if score >= 90:
        return "HIGH"
    if score >= 80:
        return "MEDIUM"
    if score >= 70:
        return "LOW"
    return "IGNORE"


def recommendation(score: int) -> str:
    """APPLY never means 'submit'. It means: worth preparing an application for review."""
    if score >= 80:
        return "APPLY"
    if score >= 70:
        return "REVIEW"
    return "SKIP"


def experience_score(min_years: int | None, candidate_years: float) -> int:
    if min_years is None:
        return 80
    gap = min_years - candidate_years
    if gap <= 0:
        return 100
    if gap <= 1:
        return 85
    if gap <= 2:
        return 65
    if gap <= 3:
        return 45
    return 20


def location_score(workplace: str, location: str | None, prefs: Preferences) -> int:
    if workplace == "remote":
        return 100 if prefs.remote else 0
    if workplace == "unknown":
        return 70
    allowed = prefs.hybrid if workplace == "hybrid" else prefs.onsite
    if not allowed:
        return 0
    if location and any(hint in location.lower() for hint in PAKISTAN_HINTS):
        return 100
    return 60 if prefs.relocation else 20


def authorization_score(workplace: str, sponsorship: str) -> int:
    """Heuristic only. The candidate's legal authorization is never assumed."""
    if sponsorship == "available":
        return 90
    if sponsorship == "not_available":
        return 60 if workplace == "remote" else 20
    return 80 if workplace == "remote" else 50


def role_score(role_tier: str) -> int:
    return {"primary": 100, "secondary": 60}.get(role_tier, 20)


def skill_key(name: str) -> str:
    """'Objective-C (basic)' -> 'objective-c'"""
    return re.sub(r"\s*\(.*?\)", "", name).strip().lower()


def skill_coverage(required: list[str], candidate_skills: list[str]) -> tuple[list[str], list[str]]:
    """(covered, missing) required technologies, checked against skills the candidate can claim."""
    keys = {skill_key(name) for name in candidate_skills}
    covered, missing = [], []
    for name in required:
        key = skill_key(name)
        if key in keys or (key in PLATFORM_ALIASES and PLATFORM_ALIASES[key] & keys):
            covered.append(name)
        else:
            missing.append(name)
    return covered, missing
