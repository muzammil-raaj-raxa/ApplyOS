import re

from app.jobs.normalization import html_to_text
from app.jobs.schemas import RawJob
from app.jobs.search_profile import SearchProfile
from app.jobs.sources.base import (
    JobSource,
    SourceError,
    SourceNotFound,
    SourceRateLimited,
    SourceResult,
    display_name,
    parse_iso,
)

API = "https://api.ashbyhq.com/posting-api/job-board"
URL_PATTERN = re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)/([0-9a-fA-F-]{36})")


def _salary(compensation) -> tuple[int | None, int | None, str | None]:
    """Yearly salary range from Ashby's compensation object (checked defensively)."""
    if not isinstance(compensation, dict):
        return None, None, None
    components = list(compensation.get("summaryComponents") or [])
    for tier in compensation.get("compensationTiers") or []:
        components.extend((tier or {}).get("components") or [])
    for item in components:
        if not isinstance(item, dict):
            continue
        if str(item.get("compensationType", "")).lower() != "salary":
            continue
        if "year" not in str(item.get("interval", "")).lower():
            continue
        low, high = item.get("minValue"), item.get("maxValue")
        if isinstance(low, (int, float)) and isinstance(high, (int, float)):
            return int(low), int(high), item.get("currencyCode")
    return None, None, None


def to_raw_job(job: dict, company: str) -> RawJob:
    workplace = job.get("workplaceType")
    if not workplace and job.get("isRemote"):
        workplace = "remote"
    low, high, currency = _salary(job.get("compensation"))
    return RawJob(
        source="ashby",
        external_id=job.get("id"),
        title=job.get("title") or "",
        company=company,
        url=job.get("jobUrl") or job.get("applyUrl") or "",
        description=job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml")),
        location=job.get("location"),
        posted_date=parse_iso(job.get("publishedAt")),
        workplace_hint=workplace,
        employment_hint=job.get("employmentType"),
        salary_min=low,
        salary_max=high,
        salary_currency=currency,
    )


class AshbySource(JobSource):
    name = "ashby"

    def _board(self, slug: str) -> list[dict]:
        data = self._get_json(f"{API}/{slug}", params={"includeCompensation": "true"})
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return [job for job in jobs if job.get("isListed", True)]

    def search(self, criteria: SearchProfile) -> SourceResult:
        result = SourceResult()
        for slug in self.slugs(criteria):
            try:
                company = display_name(slug, criteria.company_names)
                for job in self._board(slug):
                    result.jobs.append(to_raw_job(job, company))
            except SourceRateLimited as exc:
                result.errors.append(f"ashby/{slug}: {exc}")
                break
            except SourceError as exc:
                result.errors.append(f"ashby/{slug}: {exc}")
        return result

    def get_job(self, url: str) -> RawJob | None:
        match = URL_PATTERN.search(url)
        if not match:
            raise ValueError("not an Ashby job URL")
        slug, job_id = match.group(1), match.group(2).lower()
        try:
            jobs = self._board(slug)
        except SourceNotFound:
            return None
        for job in jobs:
            if str(job.get("id", "")).lower() == job_id:
                return to_raw_job(job, display_name(slug, {}))
        return None
