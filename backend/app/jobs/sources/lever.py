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
    parse_epoch_ms,
)

API = "https://api.lever.co/v0/postings"
URL_PATTERN = re.compile(r"jobs\.lever\.co/([A-Za-z0-9_.-]+)/([0-9a-fA-F-]{36})")


def _description(job: dict) -> str:
    parts = [job.get("descriptionPlain") or html_to_text(job.get("description"))]
    for item in job.get("lists") or []:
        parts.append(f"{item.get('text', '')}\n{html_to_text(item.get('content'))}")
    parts.append(job.get("additionalPlain") or html_to_text(job.get("additional")))
    return "\n\n".join(p for p in parts if p and p.strip())


def to_raw_job(job: dict, company: str) -> RawJob:
    categories = job.get("categories") or {}
    location = categories.get("location") or ", ".join(categories.get("allLocations") or []) or None
    salary = job.get("salaryRange") or {}
    low = high = currency = None
    if "year" in str(salary.get("interval", "")).lower():
        low, high, currency = salary.get("min"), salary.get("max"), salary.get("currency")
        low = int(low) if isinstance(low, (int, float)) else None
        high = int(high) if isinstance(high, (int, float)) else None
        if low is None or high is None:
            low = high = currency = None
    return RawJob(
        source="lever",
        external_id=job.get("id"),
        title=job.get("text") or "",
        company=company,
        url=job.get("hostedUrl") or job.get("applyUrl") or "",
        description=_description(job),
        location=location,
        posted_date=parse_epoch_ms(job.get("createdAt")),
        workplace_hint=job.get("workplaceType"),
        employment_hint=categories.get("commitment"),
        salary_min=low,
        salary_max=high,
        salary_currency=currency,
    )


class LeverSource(JobSource):
    name = "lever"

    def search(self, criteria: SearchProfile) -> SourceResult:
        result = SourceResult()
        for slug in self.slugs(criteria):
            try:
                data = self._get_json(f"{API}/{slug}", params={"mode": "json"})
                company = display_name(slug, criteria.company_names)
                for job in data if isinstance(data, list) else []:
                    result.jobs.append(to_raw_job(job, company))
            except SourceRateLimited as exc:
                result.errors.append(f"lever/{slug}: {exc}")
                break
            except SourceError as exc:
                result.errors.append(f"lever/{slug}: {exc}")
        return result

    def get_job(self, url: str) -> RawJob | None:
        match = URL_PATTERN.search(url)
        if not match:
            raise ValueError("not a Lever job URL")
        slug, job_id = match.group(1), match.group(2)
        try:
            data = self._get_json(f"{API}/{slug}/{job_id}")
        except SourceNotFound:
            return None
        return to_raw_job(data, display_name(slug, {}))
