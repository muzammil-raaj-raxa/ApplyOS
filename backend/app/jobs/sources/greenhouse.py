import re

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

API = "https://boards-api.greenhouse.io/v1/boards"
URL_PATTERN = re.compile(r"greenhouse\.io/(?:embed/job_app\?for=)?([A-Za-z0-9_.-]+)/jobs/(\d+)")


def to_raw_job(job: dict, company: str) -> RawJob:
    location = job.get("location")
    return RawJob(
        source="greenhouse",
        external_id=str(job["id"]) if job.get("id") is not None else None,
        title=job.get("title") or "",
        company=job.get("company_name") or company,
        url=job.get("absolute_url") or "",
        description=job.get("content") or "",
        location=location.get("name") if isinstance(location, dict) else None,
        posted_date=parse_iso(job.get("first_published") or job.get("updated_at")),
    )


class GreenhouseSource(JobSource):
    name = "greenhouse"

    def _board_name(self, token: str, overrides: dict[str, str]) -> str:
        if token in overrides:
            return overrides[token]
        try:
            data = self._get_json(f"{API}/{token}")
            if isinstance(data, dict) and data.get("name"):
                return data["name"]
        except SourceError:
            pass
        return display_name(token, overrides)

    def search(self, criteria: SearchProfile) -> SourceResult:
        result = SourceResult()
        for token in self.slugs(criteria):
            try:
                company = self._board_name(token, criteria.company_names)
                data = self._get_json(f"{API}/{token}/jobs", params={"content": "true"})
                for job in data.get("jobs", []):
                    result.jobs.append(to_raw_job(job, company))
            except SourceRateLimited as exc:
                result.errors.append(f"greenhouse/{token}: {exc}")
                break
            except SourceError as exc:
                result.errors.append(f"greenhouse/{token}: {exc}")
        return result

    def get_job(self, url: str) -> RawJob | None:
        match = URL_PATTERN.search(url) or re.search(r"for=([A-Za-z0-9_.-]+).*?(?:token|gh_jid)=(\d+)", url)
        if not match:
            raise ValueError("not a Greenhouse job URL")
        token, job_id = match.group(1), match.group(2)
        try:
            data = self._get_json(f"{API}/{token}/jobs/{job_id}")
        except SourceNotFound:
            return None
        return to_raw_job(data, display_name(token, {}))
