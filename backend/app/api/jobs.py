from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Job, UserDecision
from app.jobs.discovery import run_discovery
from app.jobs.search_profile import load_search_profile
from app.jobs.sources.ashby import AshbySource
from app.jobs.sources.base import JobSource
from app.jobs.sources.greenhouse import GreenhouseSource
from app.jobs.sources.lever import LeverSource
from app.profile.evidence import total_months_of_experience
from app.profile.validator import load_profile

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

PASSED = func.json_extract(Job.requirements_json, "$.filter.passed")
WORKPLACE = func.json_extract(Job.requirements_json, "$.workplace")


def get_sources() -> list[JobSource]:
    return [GreenhouseSource(), LeverSource(), AshbySource()]


def job_to_dict(job: Job, full: bool = False) -> dict:
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
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
    if full:
        data["description"] = job.description
    return data


def _candidate_context():
    """Years of experience and preferences from the career profile, if it loads."""
    try:
        profile = load_profile()
    except (OSError, ValueError):
        return None, None
    return total_months_of_experience(profile) / 12, profile.preferences


@router.post("/search")
def search_jobs(db: Session = Depends(get_db), sources: list[JobSource] = Depends(get_sources)):
    search = load_search_profile()
    if not any(search.companies.values()):
        raise HTTPException(400, "Add company slugs to your search profile first (PUT /api/search-profile).")
    years, prefs = _candidate_context()
    summary = run_discovery(db, sources, search, candidate_years=years, prefs=prefs)
    return summary.as_dict()


@router.get("/stats")
def job_stats(db: Session = Depends(get_db)):
    def count(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0

    return {
        "found": count(),
        "relevant": count(PASSED == 1),
        "filtered_out": count(PASSED == 0),
        "saved": count(Job.user_decision == UserDecision.SAVED.value),
        "rejected": count(Job.user_decision == UserDecision.REJECTED.value),
    }


@router.get("")
def list_jobs(
    q: str | None = None,
    source: str | None = None,
    company: str | None = None,
    workplace: Literal["remote", "hybrid", "onsite", "unknown"] | None = None,
    decision: Literal["saved", "rejected", "all"] | None = None,
    include_filtered: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Default view: relevant jobs you have not rejected, newest first."""
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

    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0
    rows = db.scalars(
        select(Job).where(*conditions).order_by(Job.created_at.desc(), Job.id.desc()).limit(limit).offset(offset)
    ).all()
    return {"total": total, "items": [job_to_dict(job) for job in rows]}


def _get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    return job_to_dict(_get_job(db, job_id), full=True)


@router.post("/{job_id}/save")
def save_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job(db, job_id)
    job.user_decision = UserDecision.SAVED.value
    db.commit()
    return job_to_dict(job)


@router.post("/{job_id}/reject")
def reject_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_job(db, job_id)
    job.user_decision = UserDecision.REJECTED.value
    db.commit()
    return job_to_dict(job)


@router.delete("/{job_id}/decision")
def clear_decision(job_id: int, db: Session = Depends(get_db)):
    job = _get_job(db, job_id)
    job.user_decision = None
    db.commit()
    return job_to_dict(job)
