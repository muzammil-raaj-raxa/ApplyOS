"""Shared fixtures for the analysis tests: a small profile, scripted AI providers, job rows."""
import copy
import json

from app.ai.base import AIProvider
from app.database.models import Job
from app.profile.validator import CareerProfile

PROFILE_DATA = {
    "profile_version": "test-v1",
    "candidate": {
        "name": "Test Person", "location": "Somewhere", "email": "t@example.com",
        "phone": "+1 000", "linkedin": "https://linkedin.example/t", "github": "https://github.example/t",
        "portfolio": "https://t.example.dev",
    },
    "target_roles": [{"title": "iOS Engineer", "tier": "primary"}, {"title": "Software Engineer", "tier": "secondary"}],
    "experience": [
        {"id": "ns", "title": "iOS Developer", "company": "NineSol", "start": "2023-03", "end": "2026-02", "bullets": [
            {"id": "ns1", "text": "Shipped iOS features in Swift.", "skills": ["Swift"]},
            {"id": "ns2", "text": "Cut crashes by 80%.", "status": "needs_confirmation",
             "note": "confirm", "safe_text": "Fixed crashes."},
        ]},
    ],
    "education": [{"degree": "BS Computer Science", "institution": "Some University", "start": "2019-10", "end": "2023-06"}],
    "skills": [
        {"name": name, "category": "iOS", "status": "confirmed",
         "evidence": [{"source": "professional_work", "description": "NineSol"}]}
        for name in ["Swift", "SwiftUI", "UIKit", "Firebase", "REST APIs", "MVVM"]
    ] + [
        {"name": "Combine", "category": "iOS", "status": "needs_evidence",
         "evidence": [{"source": "self_reported", "description": "listed only"}]},
    ],
    "projects": [
        {"id": "fb", "name": "FastBitee", "description": "Food ordering app", "technologies": ["Swift", "SwiftUI", "Firebase"],
         "bullets": [{"id": "fb1", "text": "Shipped a food ordering app.", "skills": []}]},
    ],
    "certifications": [{"name": "iOS Bootcamp", "issuer": "Udemy", "date": "2024-03"}],
    "work_authorization": {"willing_to_work": "anywhere", "legal_authorization": "not specified"},
    "preferences": {"remote": True, "hybrid": True, "onsite": True, "relocation": True},
    "salary_preferences": {"policy": "ask_every_time"},
}


def make_profile(**changes) -> CareerProfile:
    data = copy.deepcopy(PROFILE_DATA)
    data.update(changes)
    return CareerProfile.model_validate(data)


class CallbackProvider(AIProvider):
    """A fake AI. callback(prompt, call_number) returns the raw reply text, or raises."""

    def __init__(self, callback, name="groq", max_retries=3):
        super().__init__(max_retries=max_retries)
        self.name = name
        self.callback = callback
        self.prompts = []

    def is_configured(self):
        return True

    def complete(self, prompt, schema, system, tier):
        self.prompts.append(prompt)
        return self.callback(prompt, len(self.prompts)), "scripted-model"


def good_reply(technical=90, seniority=80, domain=70, ref="Swift", **extra) -> str:
    data = {
        "technical_match": technical,
        "seniority_match": seniority,
        "domain_match": domain,
        "confirmed_matches": [{"requirement": "Swift development", "evidence_ref": ref, "evidence": "Used Swift at NineSol."}],
        "partial_matches": [],
        "gaps": ["CI/CD"],
        "uncertain_requirements": [],
        "risks": [],
        "summary": "Good fit. Strong Swift background.",
    }
    data.update(extra)
    return json.dumps(data)


def add_job(session, n=1, title="iOS Engineer", required=("iOS", "Swift", "UIKit"), tier="primary",
            passed=True, workplace="remote", min_years=3, sponsorship="unknown", decision=None,
            description="Requirements:\n- Swift and UIKit", location="Remote - Worldwide") -> Job:
    job = Job(
        source="greenhouse", title=title, company=f"Co{n}", location=location,
        remote=workplace == "remote", url=f"https://x.example/{n}", description=description,
        fingerprint=f"fp-{n}", user_decision=decision,
        requirements_json={
            "required_skills": list(required), "preferred_skills": [], "minimum_years": min_years,
            "workplace": workplace, "sponsorship": sponsorship,
            "filter": {"passed": passed, "role_tier": tier, "reasons": [] if passed else ["unrelated role"]},
        },
    )
    session.add(job)
    session.commit()
    return job
