import pytest
from sqlalchemy.orm import sessionmaker

from app.database.database import Base, make_engine
from app.database.models import Job
from app.jobs.discovery import run_discovery
from app.jobs.schemas import RawJob
from app.jobs.search_profile import default_search_profile
from app.jobs.sources.base import JobSource, SourceResult
from app.profile.validator import Preferences


class FakeSource(JobSource):
    def __init__(self, name, jobs=None, errors=None, boom=None):
        super().__init__(delay=0)
        self.name = name
        self._jobs, self._errors, self._boom = jobs or [], errors or [], boom

    def search(self, criteria):
        if self._boom:
            raise self._boom
        return SourceResult(jobs=list(self._jobs), errors=list(self._errors))

    def get_job(self, url):
        return None


def raw(source="greenhouse", title="iOS Engineer", company="Acme", url="https://a.com/1", **kw):
    data = {
        "source": source, "external_id": url[-1:], "title": title, "company": company, "url": url,
        "description": "Requirements:\n- Swift and UIKit\n- 3+ years of iOS experience",
        "location": "Remote - Worldwide",
    }
    data.update(kw)
    return RawJob(**data)


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


SEARCH = default_search_profile()
PREFS = Preferences(remote=True, hybrid=True, onsite=True, relocation=True)


def run(session, *sources):
    return run_discovery(session, list(sources), SEARCH, candidate_years=3.0, prefs=PREFS)


def test_saves_normalized_jobs_with_filter_result(session):
    summary = run(session, FakeSource("greenhouse", [raw()]))
    assert (summary.fetched, summary.new, summary.relevant) == (1, 1, 1)
    job = session.query(Job).one()
    assert job.title == "iOS Engineer" and job.remote is True and len(job.fingerprint) == 64
    req = job.requirements_json
    assert req["filter"] == {"passed": True, "role_tier": "primary", "reasons": []}
    assert "Swift" in req["required_skills"] and req["minimum_years"] == 3


def test_second_run_finds_nothing_new(session):
    source = FakeSource("greenhouse", [raw()])
    run(session, source)
    summary = run(session, source)
    assert (summary.new, summary.already_known) == (0, 1)
    assert session.query(Job).count() == 1


def test_same_job_from_two_sources_is_stored_once(session):
    first = FakeSource("greenhouse", [raw(title="Senior iOS Engineer", company="Acme Inc", url="https://a.com/1")])
    second = FakeSource("lever", [raw(source="lever", company="Acme", title="Sr. iOS Engineer", url="https://lever.co/acme/2")])
    run(session, first)
    summary = run(session, second)
    assert summary.cross_source_duplicates == 1 and summary.new == 0
    assert session.query(Job).count() == 1


def test_irrelevant_jobs_are_stored_but_marked_filtered(session):
    summary = run(session, FakeSource("greenhouse", [raw(title="Account Executive", url="https://a.com/9")]))
    assert (summary.new, summary.relevant, summary.filtered_out) == (1, 0, 1)
    job = session.query(Job).one()
    assert job.requirements_json["filter"]["passed"] is False
    assert "unrelated role" in job.requirements_json["filter"]["reasons"]


def test_job_without_url_is_skipped_and_reported(session):
    summary = run(session, FakeSource("greenhouse", [raw(url=""), raw(url="https://a.com/2")]))
    assert summary.parse_failures == 1 and summary.new == 1
    assert any("missing a title, company, or URL" in error for error in summary.errors)


def test_empty_description_is_saved_with_a_parsing_error(session):
    summary = run(session, FakeSource("greenhouse", [raw(description="")]))
    assert summary.new == 1 and summary.parse_failures == 1
    assert session.query(Job).one().parsing_error == "empty description"


def test_a_crashing_source_does_not_stop_the_others(session):
    bad = FakeSource("lever", boom=RuntimeError("site is down"))
    good = FakeSource("greenhouse", [raw()])
    summary = run(session, bad, good)
    assert summary.new == 1
    assert summary.errors == ["lever: site is down"]


def test_source_errors_are_passed_through(session):
    summary = run(session, FakeSource("ashby", errors=["ashby/nope: not found (check the company slug)"]))
    assert summary.errors == ["ashby/nope: not found (check the company slug)"]


def test_existing_database_jobs_count_as_known(session):
    run(session, FakeSource("greenhouse", [raw()]))
    fresh_run = run_discovery(session, [FakeSource("lever", [raw(source="lever", url="https://lever.co/a/3")])], SEARCH, candidate_years=3.0, prefs=PREFS)
    assert fresh_run.cross_source_duplicates == 1  # index is rebuilt from the database each run
