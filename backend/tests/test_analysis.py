import pytest
from analysis_helpers import CallbackProvider, add_job, good_reply, make_profile
from sqlalchemy.orm import sessionmaker

from app.ai.base import AIInvalidOutputError, AIUnavailableError
from app.ai.prompts import JOB_ANALYSIS_V1, PROMPTS, get_prompt
from app.ai.router import AIRouter
from app.database.database import Base, make_engine
from app.database.models import JobScore
from app.jobs.analysis import (
    _render_prompt,
    analyze_batch,
    analyze_job,
    build_candidate_context,
    latest_score,
)


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


PROFILE = make_profile()


def router_for(callback, max_retries=3):
    provider = CallbackProvider(callback, max_retries=max_retries)
    return AIRouter(providers=[provider]), provider


# ---------- prompts and candidate facts ----------


def test_prompt_registry_has_versioned_ids():
    assert JOB_ANALYSIS_V1.id == "job_analysis_v1"
    assert get_prompt("job_analysis_v1") is JOB_ANALYSIS_V1
    assert "job_analysis_v1" in PROMPTS


def test_candidate_context_has_only_verified_facts_and_no_contact_details():
    context = build_candidate_context(PROFILE)
    assert "Swift" in context and "FastBitee" in context and "NineSol" in context
    assert "Combine" not in context  # skill without evidence
    assert "Cut crashes by 80%" not in context and "Fixed crashes." in context  # safe_text only
    for private in ("Test Person", "t@example.com", "+1 000", "linkedin.example", "github.example"):
        assert private not in context


def test_prompt_renders_fully_and_keeps_dollar_amounts(session):
    job = add_job(session, description="Pay is $120,000 and up. Requirements:\n- Swift")
    prompt = _render_prompt(job, PROFILE)
    assert "$120,000" in prompt
    assert "$candidate" not in prompt and "$title" not in prompt and "$description" not in prompt
    assert "iOS Engineer" in prompt and "NineSol" in prompt


def test_long_descriptions_are_truncated(session):
    job = add_job(session, description="x" * 20000)
    assert "[...description truncated]" in _render_prompt(job, PROFILE)


# ---------- analyzing one job ----------


def test_good_analysis_is_saved_with_rule_based_scores(session):
    job = add_job(session)
    router, provider = router_for(lambda prompt, n: good_reply())
    analysis, created = analyze_job(session, job, router, PROFILE)

    assert created is True
    # technical 90*30 + experience 100*20 + seniority 80*15 + location 100*10
    # + authorization 80*10 + role 100*10 + domain 70*5 = 9050 -> 91
    assert analysis["overall_score"] == 91
    assert (analysis["band"], analysis["priority"], analysis["recommendation"]) == ("Excellent", "HIGH", "APPLY")
    assert analysis["experience_match"] == 100 and analysis["location_match"] == 100
    assert analysis["authorization_match"] == 80 and analysis["role_match"] == 100
    assert analysis["skill_coverage"] == {"covered": ["iOS", "Swift", "UIKit"], "missing": []}
    assert analysis["prompt_version"] == "job_analysis_v1" and analysis["profile_version"] == "test-v1"
    assert any("legal work authorization" in risk for risk in analysis["risks"])

    row = session.query(JobScore).one()
    assert row.overall_score == 91 and row.technical_score == 90 and row.domain_score == 70
    assert row.model == "groq:scripted-model" and row.prompt_version == "job_analysis_v1"
    assert row.analysis_json["summary"].startswith("Good fit")


def test_fabricated_evidence_is_rejected_then_corrected(session):
    job = add_job(session)
    replies = [good_reply(ref="Kotlin"), good_reply(ref="Swift")]
    router, provider = router_for(lambda prompt, n: replies[n - 1])
    analysis, _ = analyze_job(session, job, router, PROFILE)
    assert analysis["confirmed_matches"][0]["evidence_ref"] == "Swift"
    assert "not a skill, project, or employer" in provider.prompts[1]


def test_evidence_can_cite_projects_and_employers(session):
    job = add_job(session)
    router, _ = router_for(lambda prompt, n: good_reply(ref="FastBitee"))
    analysis, _ = analyze_job(session, job, router, PROFILE)
    assert analysis["confirmed_matches"][0]["evidence_ref"] == "FastBitee"


def test_unproven_skill_cannot_be_cited(session):
    job = add_job(session)
    router, _ = router_for(lambda prompt, n: good_reply(ref="Combine"), max_retries=2)
    with pytest.raises(AIInvalidOutputError):
        analyze_job(session, job, router, PROFILE)


def test_always_fabricating_marks_job_needs_review_and_saves_no_score(session):
    job = add_job(session)
    router, provider = router_for(lambda prompt, n: good_reply(ref="Kotlin"), max_retries=2)
    with pytest.raises(AIInvalidOutputError):
        analyze_job(session, job, router, PROFILE)
    assert session.query(JobScore).count() == 0
    session.refresh(job)
    assert job.requirements_json["analysis_status"] == "needs_review"
    assert "needs human review" in job.requirements_json["analysis_error"]
    assert len(provider.prompts) == 2


def test_technical_score_must_agree_with_keyword_check(session):
    job = add_job(session, required=("Swift", "Kotlin", "GraphQL", "Android"))  # candidate covers 1 of 4
    replies = [good_reply(technical=95), good_reply(technical=30)]
    router, provider = router_for(lambda prompt, n: replies[n - 1])
    analysis, _ = analyze_job(session, job, router, PROFILE)
    assert analysis["technical_match"] == 30
    assert "contradicts the keyword check" in provider.prompts[1]
    assert analysis["skill_coverage"]["missing"] == ["Kotlin", "GraphQL", "Android"]


def test_ai_unavailable_saves_nothing(session):
    job = add_job(session)

    def down(prompt, n):
        raise AIUnavailableError("down")

    router, _ = router_for(down)
    with pytest.raises(AIUnavailableError):
        analyze_job(session, job, router, PROFILE)
    assert session.query(JobScore).count() == 0


def test_current_analysis_is_reused_unless_forced(session):
    job = add_job(session)
    router, provider = router_for(lambda prompt, n: good_reply())
    analyze_job(session, job, router, PROFILE)
    again, created = analyze_job(session, job, router, PROFILE)
    assert created is False and len(provider.prompts) == 1
    _, created = analyze_job(session, job, router, PROFILE, force=True)
    assert created is True and session.query(JobScore).count() == 2
    assert latest_score(session, job.id).id == 2


def test_analysis_is_redone_when_the_profile_version_changes(session):
    job = add_job(session)
    router, provider = router_for(lambda prompt, n: good_reply())
    analyze_job(session, job, router, PROFILE)
    _, created = analyze_job(session, job, router, make_profile(profile_version="test-v2"))
    assert created is True and len(provider.prompts) == 2


def test_success_clears_an_old_needs_review_marker(session):
    job = add_job(session)
    bad_router, _ = router_for(lambda prompt, n: good_reply(ref="Kotlin"), max_retries=1)
    with pytest.raises(AIInvalidOutputError):
        analyze_job(session, job, bad_router, PROFILE)
    good_router, _ = router_for(lambda prompt, n: good_reply())
    analyze_job(session, job, good_router, PROFILE, force=True)
    session.refresh(job)
    assert "analysis_status" not in job.requirements_json


def test_sponsorship_warning_is_added_as_a_risk(session):
    job = add_job(session, sponsorship="not_available", workplace="onsite", location="Berlin")
    router, _ = router_for(lambda prompt, n: good_reply())
    analysis, _ = analyze_job(session, job, router, PROFILE)
    assert any("sponsorship is not available" in risk for risk in analysis["risks"])
    assert analysis["authorization_match"] == 20 and analysis["location_match"] == 60


# ---------- batches ----------


def test_batch_scores_primary_titles_first_and_skips_ineligible_jobs(session):
    add_job(session, n=1, title="Software Engineer", tier="secondary")
    add_job(session, n=2, title="iOS Engineer", tier="primary")
    add_job(session, n=3, title="Account Executive", tier="unrelated", passed=False)
    add_job(session, n=4, title="iOS Developer", tier="primary", decision="REJECTED")
    router, _ = router_for(lambda prompt, n: good_reply())

    summary = analyze_batch(session, router, PROFILE, limit=10)
    assert summary.analyzed == 2 and summary.pending == 0 and summary.stopped_reason is None
    assert [item["title"] for item in summary.results] == ["iOS Engineer", "Software Engineer"]

    again = analyze_batch(session, router, PROFILE, limit=10)
    assert again.analyzed == 0 and again.results == []  # nothing left to score


def test_batch_respects_limit_and_reports_pending(session):
    for n in range(1, 5):
        add_job(session, n=n)
    router, _ = router_for(lambda prompt, n: good_reply())
    summary = analyze_batch(session, router, PROFILE, limit=3)
    assert summary.analyzed == 3 and summary.pending == 1


def test_batch_stops_at_the_first_unavailable_ai(session):
    for n in range(1, 4):
        add_job(session, n=n)

    def down(prompt, n):
        raise AIUnavailableError("down")

    router, provider = router_for(down)
    summary = analyze_batch(session, router, PROFILE, limit=3)
    assert summary.analyzed == 0 and summary.pending == 3
    assert "no AI provider available" in summary.stopped_reason
    assert len(provider.prompts) == 1  # did not keep trying every job


def test_batch_marks_bad_answers_and_continues(session):
    add_job(session, n=1, title="iOS Engineer")
    add_job(session, n=2, title="Mobile Engineer")

    def reply(prompt, n):
        return good_reply(ref="Kotlin") if "Title: Mobile Engineer" in prompt else good_reply()

    router, _ = router_for(reply, max_retries=1)
    summary = analyze_batch(session, router, PROFILE, limit=5)
    assert (summary.analyzed, summary.needs_review) == (1, 1)

    later = analyze_batch(session, router, PROFILE, limit=5)  # needs_review jobs are not retried automatically
    assert later.analyzed == 0 and later.needs_review == 0


def test_batch_pauses_between_calls(session):
    for n in range(1, 4):
        add_job(session, n=n)
    router, _ = router_for(lambda prompt, n: good_reply())
    pauses = []
    analyze_batch(session, router, PROFILE, limit=3, pause=2.5, sleep=pauses.append)
    assert pauses == [2.5, 2.5]
