import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.jobs.schemas import RawJob
from app.jobs.search_profile import SearchProfile

USER_AGENT = "ApplyOS/0.1 (personal job search tool)"


class SourceError(Exception):
    """A source could not be read."""


class SourceNotFound(SourceError):
    """HTTP 404: usually a wrong company slug."""


class SourceRateLimited(SourceError):
    """HTTP 429: stop talking to this source for now."""


@dataclass
class SourceResult:
    jobs: list[RawJob] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def parse_iso(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return to_utc_naive(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def parse_epoch_ms(value) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return None


def display_name(slug: str, overrides: dict[str, str]) -> str:
    return overrides.get(slug) or slug.replace("-", " ").replace("_", " ").title()


class JobSource(ABC):
    """One job site. Adapters are independent: a broken one never affects the others."""

    name: str

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.5, timeout: float = 30.0):
        self.client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        self.delay = delay  # polite pause after every request
        self.timeout = timeout

    def _get_json(self, url: str, params: dict | None = None):
        try:
            response = self.client.get(url, params=params, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise SourceError(f"request failed: {type(exc).__name__}") from exc
        finally:
            if self.delay:
                time.sleep(self.delay)
        if response.status_code == 404:
            raise SourceNotFound("not found (check the company slug)")
        if response.status_code == 429:
            raise SourceRateLimited("rate limited (HTTP 429); try again later")
        if response.status_code != 200:
            raise SourceError(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise SourceError("response was not valid JSON") from exc

    def slugs(self, criteria: SearchProfile) -> list[str]:
        return criteria.companies.get(self.name, [])

    @abstractmethod
    def search(self, criteria: SearchProfile) -> SourceResult:
        """Fetch jobs for every company configured for this source."""

    @abstractmethod
    def get_job(self, url: str) -> RawJob | None:
        """Fetch one job by its public URL. None means it no longer exists (closed)."""
