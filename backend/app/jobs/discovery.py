import logging
from dataclasses import dataclass, field

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Job
from app.jobs.deduplication import DedupIndex
from app.jobs.filtering import filter_job
from app.jobs.normalization import normalize
from app.jobs.search_profile import SearchProfile
from app.jobs.sources.base import JobSource
from app.profile.validator import Preferences

logger = logging.getLogger("applyos.jobs")


@dataclass
class DiscoverySummary:
    fetched: int = 0
    new: int = 0
    relevant: int = 0  # new jobs that passed the deterministic filters
    filtered_out: int = 0  # new jobs stored but marked not relevant
    already_known: int = 0
    cross_source_duplicates: int = 0
    parse_failures: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def run_discovery(
    session: Session,
    sources: list[JobSource],
    search: SearchProfile,
    *,
    candidate_years: float | None = None,
    prefs: Preferences | None = None,
) -> DiscoverySummary:
    """Search -> normalize -> remove duplicates -> filter -> save. One broken source or job
    never stops the run; every problem is recorded in summary.errors."""
    summary = DiscoverySummary()
    index = DedupIndex.from_session(session)

    for source in sources:
        try:
            result = source.search(search)
        except Exception as exc:  # a source must never take the whole run down
            logger.warning("source %s failed: %s", source.name, exc)
            summary.errors.append(f"{source.name}: {exc}")
            continue
        summary.errors.extend(result.errors)

        for raw in result.jobs:
            summary.fetched += 1
            try:
                job = normalize(raw)
            except ValueError as exc:
                summary.parse_failures += 1
                summary.errors.append(f"{raw.source}: skipped a job ({exc})")
                continue

            reason = index.check(job.fingerprint, job.source, job.company_key, job.title_key, job.location_key)
            if reason:
                if reason == "already stored":
                    summary.already_known += 1
                else:
                    summary.cross_source_duplicates += 1
                continue

            verdict = filter_job(job, search, prefs, candidate_years)
            if job.parsing_error:
                summary.parse_failures += 1
            row = Job(
                source=job.source,
                external_id=job.external_id,
                title=job.title,
                company=job.company,
                location=job.location,
                remote=job.remote,
                url=job.url,
                description=job.description,
                posted_date=job.posted_date,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                fingerprint=job.fingerprint,
                requirements_json={**job.requirements, "filter": verdict.as_dict()},
                parsing_error=job.parsing_error,
            )
            try:
                with session.begin_nested():
                    session.add(row)
            except IntegrityError:
                summary.already_known += 1
                continue
            index.add(job.fingerprint, job.source, job.company_key, job.title_key, job.location_key)
            summary.new += 1
            if verdict.passed:
                summary.relevant += 1
            else:
                summary.filtered_out += 1

    session.commit()
    logger.info("discovery finished: %s", summary.as_dict())
    return summary
