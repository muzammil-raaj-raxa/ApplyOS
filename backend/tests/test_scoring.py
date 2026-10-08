import pytest

from app.jobs import scoring
from app.profile.validator import Preferences

PREFS = Preferences(remote=True, hybrid=True, onsite=True, relocation=True)


def test_weights_add_up_to_100():
    assert sum(scoring.WEIGHTS.values()) == 100


def test_overall_score_is_weighted_and_rounded_half_up():
    perfect = {name: 100 for name in scoring.WEIGHTS}
    assert scoring.overall_score(perfect) == 100
    zero = {name: 0 for name in scoring.WEIGHTS}
    assert scoring.overall_score(zero) == 0
    only_technical = dict(zero, technical=100)
    assert scoring.overall_score(only_technical) == 30
    half = dict(zero, domain=50, role=5)  # (5*50 + 10*5) / 100 = 3.0
    assert scoring.overall_score(half) == 3
    tie = dict(zero, domain=10)  # 50 / 100 = 0.5 -> rounds up to 1
    assert scoring.overall_score(tie) == 1


@pytest.mark.parametrize(
    "score,band,priority,recommendation",
    [
        (100, "Excellent", "CRITICAL", "APPLY"),
        (95, "Excellent", "CRITICAL", "APPLY"),
        (94, "Excellent", "HIGH", "APPLY"),
        (90, "Excellent", "HIGH", "APPLY"),
        (89, "Strong", "MEDIUM", "APPLY"),
        (80, "Strong", "MEDIUM", "APPLY"),
        (79, "Review", "LOW", "REVIEW"),
        (70, "Review", "LOW", "REVIEW"),
        (69, "Low priority", "IGNORE", "SKIP"),
        (60, "Low priority", "IGNORE", "SKIP"),
        (59, "Reject", "IGNORE", "SKIP"),
    ],
)
def test_bands_priorities_and_recommendations(score, band, priority, recommendation):
    assert scoring.band(score) == band
    assert scoring.priority(score) == priority
    assert scoring.recommendation(score) == recommendation


def test_experience_score():
    assert scoring.experience_score(None, 3.0) == 80
    assert scoring.experience_score(3, 3.0) == 100
    assert scoring.experience_score(4, 3.0) == 85
    assert scoring.experience_score(5, 3.0) == 65
    assert scoring.experience_score(6, 3.0) == 45
    assert scoring.experience_score(8, 3.0) == 20


def test_location_score():
    assert scoring.location_score("remote", "Remote", PREFS) == 100
    assert scoring.location_score("unknown", None, PREFS) == 70
    assert scoring.location_score("onsite", "Berlin", PREFS) == 60
    assert scoring.location_score("hybrid", "Lahore, Pakistan", PREFS) == 100
    no_relocation = Preferences(remote=True, hybrid=True, onsite=True, relocation=False)
    assert scoring.location_score("onsite", "Berlin", no_relocation) == 20
    no_onsite = Preferences(remote=True, hybrid=True, onsite=False, relocation=True)
    assert scoring.location_score("onsite", "Berlin", no_onsite) == 0


def test_authorization_and_role_scores():
    assert scoring.authorization_score("onsite", "available") == 90
    assert scoring.authorization_score("onsite", "not_available") == 20
    assert scoring.authorization_score("remote", "not_available") == 60
    assert scoring.authorization_score("remote", "unknown") == 80
    assert scoring.authorization_score("onsite", "unknown") == 50
    assert (scoring.role_score("primary"), scoring.role_score("secondary"), scoring.role_score("unrelated")) == (100, 60, 20)


def test_skill_coverage_strips_notes_and_expands_ios():
    candidate = ["Swift", "UIKit", "Objective-C (basic)", "REST APIs"]
    covered, missing = scoring.skill_coverage(["iOS", "Swift", "Objective-C", "Kotlin", "GraphQL"], candidate)
    assert covered == ["iOS", "Swift", "Objective-C"]
    assert missing == ["Kotlin", "GraphQL"]


def test_ios_is_not_covered_without_any_apple_skill():
    covered, missing = scoring.skill_coverage(["iOS"], ["Python", "React"])
    assert covered == [] and missing == ["iOS"]
