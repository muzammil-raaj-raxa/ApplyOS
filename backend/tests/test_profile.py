import copy
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import profile as profile_api
from app.profile import validator
from app.profile.evidence import (
    bullets_needing_confirmation,
    gap_report,
    skills_needing_evidence,
    total_months_of_experience,
    usable_skills,
)
from app.profile.validator import CareerProfile, load_profile

SAMPLE = {
    "profile_version": "test",
    "candidate": {
        "name": "Test Person", "location": "Somewhere", "email": "t@example.com",
        "phone": "+1 000", "linkedin": "t", "github": "t", "portfolio": "t.dev",
    },
    "target_roles": [{"title": "iOS Engineer", "tier": "primary"}],
    "experience": [
        {"id": "a", "title": "Dev", "company": "A", "start": "2023-07", "end": "2024-10", "bullets": [
            {"id": "a1", "text": "Built things.", "skills": ["Swift"]},
            {"id": "a2", "text": "Cut bugs by 50%.", "status": "needs_confirmation",
             "note": "confirm the number", "safe_text": "Fixed bugs."},
        ]},
        {"id": "b", "title": "Dev", "company": "B", "start": "2025-03", "end": "2025-10"},
        {"id": "c", "title": "Dev", "company": "C", "start": "2025-11"},
    ],
    "education": [],
    "skills": [
        {"name": "Swift", "category": "Languages", "status": "confirmed",
         "evidence": [{"source": "professional_work", "description": "Company A"}]},
        {"name": "Combine", "category": "Reactive", "status": "needs_evidence",
         "evidence": [{"source": "self_reported", "description": "listed only"}]},
    ],
    "projects": [],
    "certifications": [],
    "preferences": {"remote": True, "hybrid": True, "onsite": False, "relocation": False},
}


def make_profile(**changes):
    data = copy.deepcopy(SAMPLE)
    data.update(changes)
    return CareerProfile.model_validate(data)


def test_sample_profile_is_valid():
    profile = make_profile()
    assert profile.candidate.name == "Test Person"


def test_confirmed_skill_without_real_evidence_is_rejected():
    skills = [{"name": "Swift", "category": "L", "status": "confirmed",
               "evidence": [{"source": "self_reported", "description": "trust me"}]}]
    with pytest.raises(ValidationError):
        make_profile(skills=skills, experience=[])


def test_user_confirmed_skill_is_accepted():
    skills = [{"name": "Swift", "category": "L", "status": "confirmed",
               "evidence": [{"source": "user_confirmed", "description": "confirmed by the user"}]}]
    profile = make_profile(skills=skills, experience=[])
    assert usable_skills(profile) == ["Swift"]


def test_unknown_skill_tag_is_rejected():
    experience = [{"id": "a", "title": "Dev", "company": "A", "start": "2023-07",
                   "bullets": [{"id": "a1", "text": "x", "skills": ["Fastlane"]}]}]
    with pytest.raises(ValidationError):
        make_profile(experience=experience)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(favorite_color="blue")


def test_bad_date_format_is_rejected():
    experience = [{"id": "a", "title": "Dev", "company": "A", "start": "July 2023"}]
    with pytest.raises(ValidationError):
        make_profile(experience=experience)


def test_flagged_bullet_without_note_is_rejected():
    experience = [{"id": "a", "title": "Dev", "company": "A", "start": "2023-07",
                   "bullets": [{"id": "a1", "text": "x", "status": "needs_confirmation"}]}]
    with pytest.raises(ValidationError):
        make_profile(experience=experience)


def test_usable_skills_excludes_unproven_ones():
    profile = make_profile()
    assert usable_skills(profile) == ["Swift"]
    assert skills_needing_evidence(profile) == ["Combine"]


def test_flagged_bullet_uses_safe_text_only():
    profile = make_profile()
    bullets = profile.experience[0].bullets
    assert bullets[0].usable_text() == "Built things."
    assert bullets[1].usable_text() == "Fixed bugs."
    assert len(bullets_needing_confirmation(profile)) == 1


def test_months_of_experience_counts_both_end_months():
    # 16 + 8 + 12 months (Nov 2025 to Oct 2026 inclusive) = 36
    assert total_months_of_experience(make_profile(), today=date(2026, 10, 6)) == 36


def test_overlapping_jobs_are_not_double_counted():
    experience = [
        {"id": "a", "title": "Dev", "company": "A", "start": "2024-01", "end": "2024-12"},
        {"id": "b", "title": "Dev", "company": "B", "start": "2024-06", "end": "2025-02"},
    ]
    assert total_months_of_experience(make_profile(experience=experience)) == 14


def test_gap_report_lists_missing_fields():
    report = gap_report(make_profile())
    assert "work_authorization" in report["missing_fields"]
    assert "salary_preferences" in report["missing_fields"]


def test_real_profile_file_is_valid():
    if not validator.PROFILE_PATH.exists():
        pytest.skip("career_profile.json not created yet")
    profile = load_profile()
    assert profile.candidate.name == "Muzammil Raza"


def make_client():
    app = FastAPI()
    app.include_router(profile_api.router)
    return TestClient(app)


def test_api_returns_404_when_profile_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(validator, "PROFILE_PATH", tmp_path / "missing.json")
    assert make_client().get("/api/profile").status_code == 404


def test_api_returns_422_when_profile_invalid(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"profile_version": "x"}', encoding="utf-8")
    monkeypatch.setattr(validator, "PROFILE_PATH", bad)
    assert make_client().get("/api/profile").status_code == 422


def test_api_returns_profile_and_gaps(monkeypatch, tmp_path):
    import json
    good = tmp_path / "good.json"
    good.write_text(json.dumps(SAMPLE), encoding="utf-8")
    monkeypatch.setattr(validator, "PROFILE_PATH", good)
    body = make_client().get("/api/profile").json()
    assert body["profile"]["candidate"]["name"] == "Test Person"
    assert "gaps" in body and "experience" in body
