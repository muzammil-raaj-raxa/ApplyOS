import httpx
import pytest

from app.jobs.search_profile import SearchProfile
from app.jobs.sources.ashby import AshbySource
from app.jobs.sources.base import USER_AGENT
from app.jobs.sources.greenhouse import GreenhouseSource
from app.jobs.sources.lever import LeverSource


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def profile(**companies) -> SearchProfile:
    return SearchProfile(companies=companies)


# ---------- Greenhouse ----------

GH_JOB = {
    "id": 4001,
    "title": "iOS Engineer",
    "absolute_url": "https://boards.greenhouse.io/stripe/jobs/4001",
    "location": {"name": "Remote - Worldwide"},
    "updated_at": "2026-06-02T08:58:57-04:00",
    "content": "&lt;p&gt;Build apps with Swift.&lt;/p&gt;",
}


def gh_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/v1/boards/stripe":
        return httpx.Response(200, json={"name": "Stripe"})
    if path == "/v1/boards/stripe/jobs":
        assert request.url.params["content"] == "true"
        return httpx.Response(200, json={"jobs": [GH_JOB]})
    if path == "/v1/boards/stripe/jobs/4001":
        return httpx.Response(200, json=GH_JOB)
    return httpx.Response(404)


def test_greenhouse_search_maps_fields():
    source = GreenhouseSource(client=client_for(gh_handler), delay=0)
    result = source.search(profile(greenhouse=["stripe"]))
    assert result.errors == []
    job = result.jobs[0]
    assert (job.source, job.company, job.title) == ("greenhouse", "Stripe", "iOS Engineer")
    assert job.url.endswith("/jobs/4001") and job.external_id == "4001"
    assert job.location == "Remote - Worldwide"
    assert job.posted_date is not None and "&lt;" in job.description  # cleaned later, in normalization


def test_greenhouse_wrong_slug_is_reported_and_others_still_run():
    source = GreenhouseSource(client=client_for(gh_handler), delay=0)
    result = source.search(profile(greenhouse=["nope", "stripe"]))
    assert len(result.jobs) == 1
    assert result.errors == ["greenhouse/nope: not found (check the company slug)"]


def test_greenhouse_rate_limit_stops_remaining_companies():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(429)

    source = GreenhouseSource(client=client_for(handler), delay=0)
    result = source.search(profile(greenhouse=["a", "b", "c"]))
    assert len(result.errors) == 1 and "rate limited" in result.errors[0]
    assert all("/boards/a" in path for path in calls)  # never touched b or c


def test_greenhouse_get_job_and_closed_job():
    source = GreenhouseSource(client=client_for(gh_handler), delay=0)
    assert source.get_job("https://boards.greenhouse.io/stripe/jobs/4001").title == "iOS Engineer"
    assert source.get_job("https://boards.greenhouse.io/stripe/jobs/9999") is None
    with pytest.raises(ValueError):
        source.get_job("https://example.com/not-greenhouse")


def test_requests_send_a_user_agent():
    seen = []

    def handler(request):
        seen.append(request.headers.get("user-agent"))
        return httpx.Response(200, json={"jobs": []})

    client = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": USER_AGENT})
    GreenhouseSource(client=client, delay=0).search(profile(greenhouse=["stripe"]))
    assert seen and all(agent == USER_AGENT for agent in seen)


# ---------- Lever ----------

LEVER_ID = "11111111-2222-3333-4444-555555555555"
LEVER_JOB = {
    "id": LEVER_ID,
    "text": "Senior iOS Developer",
    "hostedUrl": f"https://jobs.lever.co/spotify/{LEVER_ID}",
    "createdAt": 1767225600000,
    "workplaceType": "hybrid",
    "categories": {"location": "Stockholm", "commitment": "Full-time"},
    "descriptionPlain": "Build the player.",
    "lists": [{"text": "Requirements", "content": "<li>Swift</li><li>UIKit</li>"}],
    "additionalPlain": "We value diversity.",
    "salaryRange": {"min": 90000, "max": 120000, "currency": "EUR", "interval": "per-year-salary"},
}


def lever_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/v0/postings/spotify":
        assert request.url.params["mode"] == "json"
        return httpx.Response(200, json=[LEVER_JOB])
    if path == f"/v0/postings/spotify/{LEVER_ID}":
        return httpx.Response(200, json=LEVER_JOB)
    return httpx.Response(404)


def test_lever_search_maps_fields():
    source = LeverSource(client=client_for(lever_handler), delay=0)
    job = source.search(profile(lever=["spotify"])).jobs[0]
    assert (job.company, job.title, job.location) == ("Spotify", "Senior iOS Developer", "Stockholm")
    assert job.workplace_hint == "hybrid" and job.employment_hint == "Full-time"
    assert (job.salary_min, job.salary_max, job.salary_currency) == (90000, 120000, "EUR")
    assert job.posted_date is not None
    assert "Build the player." in job.description and "- Swift" in job.description
    assert "We value diversity." in job.description


def test_lever_hourly_salary_is_ignored():
    hourly = dict(LEVER_JOB, salaryRange={"min": 40, "max": 60, "currency": "USD", "interval": "per-hour-wage"})
    source = LeverSource(client=client_for(lambda r: httpx.Response(200, json=[hourly])), delay=0)
    job = source.search(profile(lever=["spotify"])).jobs[0]
    assert job.salary_min is None and job.salary_max is None


def test_lever_unknown_slug_and_get_job():
    source = LeverSource(client=client_for(lever_handler), delay=0)
    assert source.search(profile(lever=["nope"])).errors == ["lever/nope: not found (check the company slug)"]
    assert source.get_job(f"https://jobs.lever.co/spotify/{LEVER_ID}").title == "Senior iOS Developer"
    assert source.get_job("https://jobs.lever.co/spotify/99999999-2222-3333-4444-555555555555") is None


# ---------- Ashby ----------

ASHBY_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ASHBY_JOBS = {
    "jobs": [
        {
            "id": ASHBY_ID,
            "title": "iOS Engineer",
            "location": "New York, NY",
            "isRemote": True,
            "workplaceType": "Hybrid",
            "employmentType": "FullTime",
            "isListed": True,
            "publishedAt": "2026-04-07T17:12:35.753+00:00",
            "jobUrl": f"https://jobs.ashbyhq.com/ramp/{ASHBY_ID}",
            "applyUrl": f"https://jobs.ashbyhq.com/ramp/{ASHBY_ID}/application",
            "descriptionPlain": "Build the Ramp app.",
            "compensation": {
                "summaryComponents": [
                    {"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "USD",
                     "minValue": 150000, "maxValue": 200000}
                ]
            },
        },
        {"id": "hidden", "title": "Secret Job", "isListed": False, "jobUrl": "https://jobs.ashbyhq.com/ramp/hidden"},
    ]
}


def ashby_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/posting-api/job-board/ramp":
        assert request.url.params["includeCompensation"] == "true"
        return httpx.Response(200, json=ASHBY_JOBS)
    return httpx.Response(404)


def test_ashby_search_maps_fields_and_skips_unlisted():
    source = AshbySource(client=client_for(ashby_handler), delay=0)
    result = source.search(profile(ashby=["ramp"]))
    assert [job.title for job in result.jobs] == ["iOS Engineer"]
    job = result.jobs[0]
    assert job.workplace_hint == "Hybrid"  # workplaceType beats isRemote
    assert (job.salary_min, job.salary_max, job.salary_currency) == (150000, 200000, "USD")
    assert job.employment_hint == "FullTime" and job.url.endswith(ASHBY_ID)


def test_ashby_get_job_by_url():
    source = AshbySource(client=client_for(ashby_handler), delay=0)
    assert source.get_job(f"https://jobs.ashbyhq.com/ramp/{ASHBY_ID}").title == "iOS Engineer"
    assert source.get_job("https://jobs.ashbyhq.com/ramp/00000000-bbbb-cccc-dddd-eeeeeeeeeeee") is None
    assert source.get_job(f"https://jobs.ashbyhq.com/gone/{ASHBY_ID}") is None


def test_source_timeout_is_an_error_not_a_crash():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    result = AshbySource(client=client_for(handler), delay=0).search(profile(ashby=["ramp"]))
    assert result.jobs == [] and "request failed: ReadTimeout" in result.errors[0]
