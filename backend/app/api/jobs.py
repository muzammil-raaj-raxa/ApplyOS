from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.ai.base import AIInvalidOutputError, AIUnavailableError
from app.ai.router import ai_router
from app.config import settings
from app.database.database import get_db
from app.database.models import Job, JobScore, UserDecision
from app.jobs.analysis import analyze_batch, analyze_job, latest_score
from app.jobs.discovery import run_discovery
from app.jobs.search_profile import load_search_profile
from app.jobs.sources.ashby import AshbySource
from app.jobs.sources.base import JobSource
from app.jobs.sources.greenhouse import GreenhouseSource
from app.jobs.sources.lever import LeverSource
from app.profile.evidence import total_months_of_experience
from app.profile.validator import CareerProfile, load_profile

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

PASSED = func.json_extract(Job.requirements_json, "$.filter.passed")
WORKPLACE = func.json_extract(Job.requirements_json, "$.workplace")


def get_sources() -> list[JobSource]:
    return [GreenhouseSource(), LeverSource(), AshbySource()]


def get_router():
    return ai_router


def score_summary(score: JobScore | None) -> dict | None:
    if score is None:
        return None
    analysis = score.analysis_json or {}
    return {
        "overall_score": score.overall_score,
        "band": analysis.get("band"),
        "recommendation": analysis.get("recommendation"),
        "priority": analysis.get("priority"),
        "technical": score.technical_score,
        "experience": score.experience_score,
        "seniority": score.seniority_score,
        "location": score.location_score,
        "authorization": score.authorization_score,
        "role": score.role_score,
        "domain": score.domain_score,
        "matched": analysis.get("skill_coverage", {}).get("covered", []),
        "gaps": analysis.get("gaps", []),
        "model": score.model,
        "prompt_version": score.prompt_version,
        "analyzed_at": score.created_at.isoformat() if score.created_at else None,
    }


def job_to_dict(job: Job, score: JobScore | None = None, full: bool = False) -> dict:
    req = job.requirements_json or {}
    verdict = req.get("filter", {})
    data = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote": job.remote,
        "workplace": req.get("workplace"),
        "url": job.url,
        "source": job.source,
        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": req.get("salary_currency"),
        "employment_type": req.get("employment_type"),
        "required_skills": req.get("required_skills", []),
        "preferred_skills": req.get("preferred_skills", []),
        "minimum_years": req.get("minimum_years"),
        "sponsorship": req.get("sponsorship"),
        "relevant": verdict.get("passed"),
        "role_tier": verdict.get("role_tier"),
        "filter_reasons": verdict.get("reasons", []),
        "user_decision": job.user_decision,
        "parsing_error": job.parsing_error,
        "analysis_status": req.get("analysis_status"),
        "score": score_summary(score),
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
    if full:
        data["description"] = job.description
        data["analysis"] = score.analysis_json if score else None
        data["analysis_error"] = req.get("analysis_error")
    return data


def _candidate_context():
    """Years of experience and preferences from the career profile, if it loads."""
    try:
        profile = load_profile()
    except (OSError, ValueError):
        return None, None
    return total_months_of_experience(profile) / 12, profile.preferences


def _load_profile_or_409() -> CareerProfile:
    try:
        return load_profile()
    except (OSError, ValueError) as exc:
        raise HTTPException(409, f"Career profile is missing or invalid: {exc}")


@router.post("/search")
def search_jobs(db: Session = Depends(get_db), sources: list[JobSource] = Depends(get_sources)):
    search = load_search_profile()
    if not any(search.companies.values()):
        raise HTTPException(400, "Add company slugs to your search profile first (PUT /api/search-profile).")
    years, prefs = _candidate_context()
    summary = run_discovery(db, sources, search, candidate_years=years, prefs=prefs)
    return summary.as_dict()


@router.post("/analyze")
def analyze_pending_jobs(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    ai=Depends(get_router),
):
    """Score the most promising unscored jobs. Stops early if no AI provider is available."""
    profile = _load_profile_or_409()
    summary = analyze_batch(db, ai, profile, limit=limit, pause=settings.ai_batch_pause_seconds)
    return summary.as_dict()


@router.get("/stats")
def job_stats(db: Session = Depends(get_db)):
    def count(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0

    latest_ids = select(func.max(JobScore.id)).group_by(JobScore.job_id).scalar_subquery()
    threshold = load_search_profile().minimum_score
    return {
        "found": count(),
        "relevant": count(PASSED == 1),
        "filtered_out": count(PASSED == 0),
        "saved": count(Job.user_decision == UserDecision.SAVED.value),
        "rejected": count(Job.user_decision == UserDecision.REJECTED.value),
        "analyzed": db.scalar(select(func.count(func.distinct(JobScore.job_id)))) or 0,
        "high_fit": db.scalar(
            select(func.count()).select_from(JobScore).where(JobScore.id.in_(latest_ids), JobScore.overall_score >= threshold)
        )
        or 0,
    }


@router.get("")
def list_jobs(
    q: str | None = None,
    source: str | None = None,
    company: str | None = None,
    workplace: Literal["remote", "hybrid", "onsite", "unknown"] | None = None,
    decision: Literal["saved", "rejected", "all"] | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    scored: bool | None = None,
    sort: Literal["newest", "score"] = "newest",
    include_filtered: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Default view: relevant jobs you have not rejected, newest first."""
    latest = (
        select(JobScore.job_id.label("jid"), func.max(JobScore.id).label("mid"))
        .group_by(JobScore.job_id)
        .subquery()
    )
    score = aliased(JobScore)

    conditions = []
    if not include_filtered:
        conditions.append(PASSED == 1)
    if q:
        like = f"%{q}%"
        conditions.append(or_(Job.title.ilike(like), Job.company.ilike(like)))
    if source:
        conditions.append(Job.source == source)
    if company:
        conditions.append(Job.company.ilike(f"%{company}%"))
    if workplace:
        conditions.append(WORKPLACE == workplace)
    if decision == "saved":
        conditions.append(Job.user_decision == UserDecision.SAVED.value)
    elif decision == "rejected":
        conditions.append(Job.user_decision == UserDecision.REJECTED.value)
    elif decision is None:
        conditions.append(or_(Job.user_decision.is_(None), Job.user_decision != UserDecision.REJECTED.value))
    if min_score is not None:
        conditions.append(score.overall_score >= min_score)
    if scored is True:
        conditions.append(score.id.is_not(None))
    elif scored is False:
        conditions.append(score.id.is_(None))

    joins = (latest, latest.c.jid == Job.id), (score, score.id == latest.c.mid)
    count_stmt = select(func.count()).select_from(Job)
    rows_stmt = select(Job, score).select_from(Job)
    for target, on in joins:
        count_stmt = count_stmt.outerjoin(target, on)
        rows_stmt = rows_stmt.outerjoin(target, on)

    order = [Job.created_at.desc(), Job.id.desc()]
    if sort == "score":
        order = [score.overall_score.desc().nulls_last(), *order]

    total = db.scalar(count_stmt.where(*conditions)) or 0
    rows = db.execute(rows_stmt.where(*conditions).order_by(*order).limit(limit).offset(offset)).all()
    return {"total": total, "items": [job_to_dict(job, row_score) for job, row_score in rows]}


def _get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job(db, job_id)
    return job_to_dict(job, latest_score(db, job.id), full=True)


@router.post("/{job_id}/analyze")
def analyze_one_job(
    job_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    ai=Depends(get_router),
):
    job = _get_job(db, job_id)
    profile = _load_profile_or_409()
    try:
        analysis, created = analyze_job(db, job, ai, profile, force=force)
    except AIUnavailableError as exc:
        raise HTTPException(503, str(exc))
    except AIInvalidOutputError as exc:
        raise HTTPException(422, f"The AI answer failed validation; the job is marked needs_review. {exc}")
    return {"created": created, "analysis": analysis}


def _set_decision(db: Session, job_id: int, decision: str | None) -> dict:
    job = _get_job(db, job_id)
    job.user_decision = decision
    db.commit()
    return job_to_dict(job, latest_score(db, job.id))


@router.post("/{job_id}/save")
def save_job(job_id: int, db: Session = Depends(get_db)):
    return _set_decision(db, job_id, UserDecision.SAVED.value)


@router.post("/{job_id}/reject")
def reject_job(job_id: int, db: Session = Depends(get_db)):
    return _set_decision(db, job_id, UserDecision.REJECTED.value)


@router.delete("/{job_id}/decision")
def clear_decision(job_id: int, db: Session = Depends(get_db)):
    return _set_decision(db, job_id, None)
