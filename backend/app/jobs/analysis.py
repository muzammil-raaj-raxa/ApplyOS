import logging
import time
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.base import AIInvalidOutputError, AIUnavailableError
from app.ai.prompts import JOB_ANALYSIS_V1
from app.database.models import Job, JobScore, UserDecision
from app.jobs import scoring
from app.profile.evidence import total_months_of_experience, usable_skills
from app.profile.validator import CareerProfile

logger = logging.getLogger("applyos.analysis")

MAX_DESCRIPTION_CHARS = 7000  # keeps one call small enough for free-tier token limits
TECH_TOLERANCE = 35  # the AI's technical score may differ this much from the keyword check
MIN_REQUIRED_FOR_CROSSCHECK = 3

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------- what the AI must return ----------


class MatchItem(BaseModel):
    requirement: str = Field(min_length=1, max_length=300)
    evidence_ref: str = Field(min_length=1, max_length=120)
    evidence: str = Field(min_length=1, max_length=400)


class PartialItem(BaseModel):
    requirement: str = Field(min_length=1, max_length=300)
    evidence_ref: str = Field(min_length=1, max_length=120)
    note: str = Field(min_length=1, max_length=400)


class JobAnalysisAI(BaseModel):
    """Only what needs judgment. Experience, location, authorization and role are computed
    by rules, and the overall score is computed from the weights, never by the AI."""

    technical_match: int = Field(ge=0, le=100)
    seniority_match: int = Field(ge=0, le=100)
    domain_match: int = Field(ge=0, le=100)
    confirmed_matches: list[MatchItem] = Field(default_factory=list, max_length=15)
    partial_matches: list[PartialItem] = Field(default_factory=list, max_length=15)
    gaps: list[str] = Field(default_factory=list, max_length=15)
    uncertain_requirements: list[str] = Field(default_factory=list, max_length=15)
    risks: list[str] = Field(default_factory=list, max_length=10)
    summary: str = Field(min_length=1, max_length=600)


# ---------- candidate facts sent to the AI ----------


def _month(year_month: str | None) -> str:
    if not year_month:
        return "present"
    year, month = year_month.split("-")
    return f"{MONTH_NAMES[int(month) - 1]} {year}"


def build_candidate_context(profile: CareerProfile) -> str:
    """Verified facts only. No name, email, phone or links: this text leaves your machine."""
    months = total_months_of_experience(profile)
    lines = [
        f"Professional experience: about {round(months / 12)} years ({months} months of employment).",
        "Target roles: " + ", ".join(role.title for role in profile.target_roles if role.tier == "primary"),
        "Skills the candidate can claim (verified): " + ", ".join(usable_skills(profile)),
        "",
        "Work history:",
    ]
    for job in profile.experience:
        lines.append(f"- {job.title}, {job.company} ({_month(job.start)} - {_month(job.end)})")
        for bullet in job.bullets:
            text = bullet.usable_text()
            if text:
                lines.append(f"  * {text}")
    lines += ["", "Projects:"]
    for project in profile.projects:
        tech = ", ".join(project.technologies)
        lines.append(f"- {project.name} ({project.description}) [{tech}]")
        for bullet in project.bullets:
            text = bullet.usable_text()
            if text:
                lines.append(f"  * {text}")
    lines += ["", "Education:"]
    for edu in profile.education:
        lines.append(f"- {edu.degree}, {edu.institution} ({_month(edu.start)} - {_month(edu.end)})")
    if profile.certifications:
        lines += ["", "Certifications:"]
        lines += [f"- {cert.name} ({cert.issuer})" for cert in profile.certifications]
    return "\n".join(lines)


def candidate_anchors(profile: CareerProfile) -> set[str]:
    """Names the AI may cite as evidence: skills, projects, employers, certifications."""
    anchors = {scoring.skill_key(name) for name in usable_skills(profile)}
    anchors |= {project.name.lower() for project in profile.projects}
    anchors |= {job.company.lower() for job in profile.experience}
    anchors |= {cert.name.lower() for cert in profile.certifications}
    return anchors


# ---------- business rules on the AI's answer (spec section 52) ----------


def make_check(profile: CareerProfile, required_skills: list[str]):
    anchors = candidate_anchors(profile)
    covered, missing = scoring.skill_coverage(required_skills, usable_skills(profile))

    def check(result: JobAnalysisAI) -> None:
        for item in [*result.confirmed_matches, *result.partial_matches]:
            if scoring.skill_key(item.evidence_ref) not in anchors:
                raise ValueError(
                    f"evidence_ref '{item.evidence_ref}' is not a skill, project, or employer in "
                    "the candidate facts. Cite only items that appear in the candidate facts."
                )
        if len(required_skills) >= MIN_REQUIRED_FOR_CROSSCHECK:
            expected = round(100 * len(covered) / len(required_skills))
            if abs(result.technical_match - expected) > TECH_TOLERANCE:
                raise ValueError(
                    f"technical_match {result.technical_match} contradicts the keyword check: the "
                    f"candidate covers {len(covered)} of {len(required_skills)} required technologies "
                    f"(about {expected}%). Missing: {', '.join(missing) or 'none'}."
                )

    return check


# ---------- building and saving one analysis ----------


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def build_analysis(job: Job, ai: JobAnalysisAI, profile: CareerProfile, provider: str, model: str) -> dict:
    req = job.requirements_json or {}
    workplace = req.get("workplace", "unknown")
    sponsorship = req.get("sponsorship", "unknown")
    required = req.get("required_skills", [])
    covered, missing = scoring.skill_coverage(required, usable_skills(profile))
    candidate_years = total_months_of_experience(profile) / 12

    scores = {
        "technical": ai.technical_match,
        "experience": scoring.experience_score(req.get("minimum_years"), candidate_years),
        "seniority": ai.seniority_match,
        "location": scoring.location_score(workplace, job.location, profile.preferences),
        "authorization": scoring.authorization_score(workplace, sponsorship),
        "role": scoring.role_score(req.get("filter", {}).get("role_tier", "unrelated")),
        "domain": ai.domain_match,
    }
    overall = scoring.overall_score(scores)

    risks = list(ai.risks)
    if sponsorship == "not_available":
        risks.append("The posting says visa sponsorship is not available or work authorization is required.")
    if profile.work_authorization.get("legal_authorization", "not specified") == "not specified":
        risks.append("Your legal work authorization for this job's country is not confirmed; the application will pause and ask you.")

    return {
        "overall_score": overall,
        "band": scoring.band(overall),
        "recommendation": scoring.recommendation(overall),
        "priority": scoring.priority(overall),
        "technical_match": scores["technical"],
        "experience_match": scores["experience"],
        "seniority_match": scores["seniority"],
        "location_match": scores["location"],
        "authorization_match": scores["authorization"],
        "role_match": scores["role"],
        "domain_match": scores["domain"],
        "confirmed_matches": [item.model_dump() for item in ai.confirmed_matches],
        "partial_matches": [item.model_dump() for item in ai.partial_matches],
        "gaps": ai.gaps,
        "uncertain_requirements": ai.uncertain_requirements,
        "risks": _dedupe(risks),
        "summary": ai.summary,
        "skill_coverage": {"covered": covered, "missing": missing},
        "scored_by": {
            "ai": ["technical", "seniority", "domain"],
            "rules": ["experience", "location", "authorization", "role", "overall"],
        },
        "weights": scoring.WEIGHTS,
        "provider": provider,
        "model": model,
        "prompt_version": JOB_ANALYSIS_V1.id,
        "profile_version": profile.profile_version,
    }


def latest_score(session: Session, job_id: int) -> JobScore | None:
    return session.scalars(
        select(JobScore).where(JobScore.job_id == job_id).order_by(JobScore.id.desc()).limit(1)
    ).first()


def _is_current(row: JobScore, profile: CareerProfile) -> bool:
    return row.prompt_version == JOB_ANALYSIS_V1.id and (row.analysis_json or {}).get("profile_version") == profile.profile_version


def _render_prompt(job: Job, profile: CareerProfile) -> str:
    req = job.requirements_json or {}
    description = job.description
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS] + "\n[...description truncated]"
    min_years = req.get("minimum_years")
    return JOB_ANALYSIS_V1.render(
        candidate=build_candidate_context(profile),
        title=job.title,
        company=job.company,
        location=job.location or "not stated",
        workplace=req.get("workplace", "unknown"),
        min_years=f"{min_years}+ years" if min_years else "not stated",
        required_skills=", ".join(req.get("required_skills", [])) or "none detected",
        preferred_skills=", ".join(req.get("preferred_skills", [])) or "none detected",
        description=description,
    )


def analyze_job(session: Session, job: Job, router, profile: CareerProfile, *, force: bool = False):
    """Returns (analysis, created). Reuses the stored analysis when it is current, unless force.
    Raises AIUnavailableError (nothing saved) or AIInvalidOutputError (job marked needs_review)."""
    existing = latest_score(session, job.id)
    if existing and not force and _is_current(existing, profile):
        return existing.analysis_json, False

    req = job.requirements_json or {}
    check = make_check(profile, req.get("required_skills", []))
    try:
        result = router.generate(
            _render_prompt(job, profile),
            JobAnalysisAI,
            system=JOB_ANALYSIS_V1.system,
            tier="strong",
            check=check,
        )
    except AIInvalidOutputError as exc:
        job.requirements_json = {**req, "analysis_status": "needs_review", "analysis_error": str(exc)[:500]}
        session.commit()
        raise

    analysis = build_analysis(job, result.data, profile, result.provider, result.model)
    session.add(
        JobScore(
            job_id=job.id,
            overall_score=analysis["overall_score"],
            technical_score=analysis["technical_match"],
            experience_score=analysis["experience_match"],
            seniority_score=analysis["seniority_match"],
            location_score=analysis["location_match"],
            authorization_score=analysis["authorization_match"],
            role_score=analysis["role_match"],
            domain_score=analysis["domain_match"],
            analysis_json=analysis,
            model=f"{result.provider}:{result.model}"[:100],
            prompt_version=JOB_ANALYSIS_V1.id,
        )
    )
    job.requirements_json = {k: v for k, v in req.items() if k not in ("analysis_status", "analysis_error")}
    session.commit()
    return analysis, True


# ---------- scoring many jobs ----------


@dataclass
class BatchSummary:
    analyzed: int = 0
    needs_review: int = 0
    pending: int = 0  # relevant jobs still waiting for a score
    stopped_reason: str | None = None
    results: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def pending_query(profile: CareerProfile):
    """Relevant, not rejected by you, has a description, and no current score yet."""
    done = select(JobScore.job_id).where(
        JobScore.prompt_version == JOB_ANALYSIS_V1.id,
        func.json_extract(JobScore.analysis_json, "$.profile_version") == profile.profile_version,
    )
    status = func.coalesce(func.json_extract(Job.requirements_json, "$.analysis_status"), "")
    return select(Job).where(
        func.json_extract(Job.requirements_json, "$.filter.passed") == 1,
        Job.id.not_in(done),
        or_(Job.user_decision.is_(None), Job.user_decision != UserDecision.REJECTED.value),
        Job.description != "",
        status != "needs_review",
    )


def analyze_batch(session, router, profile: CareerProfile, *, limit: int = 5, pause: float = 0.0, sleep=time.sleep) -> BatchSummary:
    """Score the most promising unscored jobs (iOS and Swift titles first, then newest).
    Stops at the first 'no AI available' so a rate-limited provider is never hammered."""
    summary = BatchSummary()
    query = pending_query(profile)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    tier = func.json_extract(Job.requirements_json, "$.filter.role_tier")
    jobs = session.scalars(query.order_by(tier, Job.created_at.desc(), Job.id.desc()).limit(limit)).all()

    for index, job in enumerate(jobs):
        if pause and index > 0:
            sleep(pause)
        try:
            analysis, _ = analyze_job(session, job, router, profile)
        except AIUnavailableError as exc:
            summary.stopped_reason = str(exc)
            break
        except AIInvalidOutputError:
            summary.needs_review += 1
            summary.results.append({"id": job.id, "title": job.title, "company": job.company, "status": "needs_review"})
            continue
        summary.analyzed += 1
        summary.results.append(
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "overall_score": analysis["overall_score"],
                "recommendation": analysis["recommendation"],
            }
        )
    summary.pending = max(0, total - summary.analyzed - summary.needs_review)
    logger.info("analysis batch finished: %s", summary.as_dict())
    return summary
