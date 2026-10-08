import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api import jobs as jobs_api
from app.api import search_profile as search_profile_api
from app.database.database import Base, get_db, make_engine
from app.jobs import search_profile as search_profile_module
from app.jobs.schemas import RawJob
from app.jobs.sources.base import JobSource, SourceResult


class FakeSource(JobSource):
    name = "greenhouse"

    def __init__(self, jobs):
        super().__init__(delay=0)
        self._jobs = jobs

    def search(self, criteria):
        return SourceResult(jobs=list(self._jobs))

    def get_job(self, url):
        return None


def raw(title, url, location="Remote - Worldwide", company="Acme", description="Requirements:\n- Swift"):
    return RawJob(source="greenhouse", external_id=url[-1], title=title, company=company, url=url,
                  description=description, location=location)


JOBS = [
    raw("iOS Engineer", "https://a.com/1"),
    raw("Mobile Engineer", "https://a.com/2", location="Berlin", company="Beta"),
    raw("Account Executive", "https://a.com/3"),
]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(search_profile_module, "SEARCH_PROFILE_PATH", tmp_path / "search_profile.json")
    monkeypatch.setattr(jobs_api, "_candidate_context", lambda: (3.0, None))
    app = FastAPI()
    app.include_router(jobs_api.router)
    app.include_router(search_profile_api.router)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[jobs_api.get_sources] = lambda: [FakeSource(JOBS)]
    return TestClient(app)


def test_search_requires_companies(client):
    client.put("/api/search-profile", json={"companies": {}})
    response = client.post("/api/jobs/search")
    assert response.status_code == 400


def test_search_then_list_shows_only_relevant_jobs(client):
    summary = client.post("/api/jobs/search").json()
    assert (summary["fetched"], summary["new"], summary["relevant"], summary["filtered_out"]) == (3, 3, 2, 1)
    body = client.get("/api/jobs").json()
    assert body["total"] == 2
    assert {item["title"] for item in body["items"]} == {"iOS Engineer", "Mobile Engineer"}
    everything = client.get("/api/jobs", params={"include_filtered": True}).json()
    assert everything["total"] == 3


def test_list_filters(client):
    client.post("/api/jobs/search")
    assert client.get("/api/jobs", params={"q": "mobile"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"company": "beta"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"workplace": "remote"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"source": "lever"}).json()["total"] == 0
    assert client.get("/api/jobs", params={"limit": 1}).json()["items"].__len__() == 1


def test_save_reject_and_clear(client):
    client.post("/api/jobs/search")
    items = client.get("/api/jobs").json()["items"]
    first, second = items[0]["id"], items[1]["id"]

    assert client.post(f"/api/jobs/{first}/save").json()["user_decision"] == "SAVED"
    assert client.post(f"/api/jobs/{second}/reject").json()["user_decision"] == "REJECTED"

    default_ids = {item["id"] for item in client.get("/api/jobs").json()["items"]}
    assert second not in default_ids and first in default_ids
    assert client.get("/api/jobs", params={"decision": "saved"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"decision": "rejected"}).json()["total"] == 1

    stats = client.get("/api/jobs/stats").json()
    assert stats == {"found": 3, "relevant": 2, "filtered_out": 1, "saved": 1, "rejected": 1, "analyzed": 0, "high_fit": 0}

    assert client.delete(f"/api/jobs/{second}/decision").json()["user_decision"] is None
    assert client.get("/api/jobs").json()["total"] == 2


def test_job_detail_has_description_and_404(client):
    client.post("/api/jobs/search")
    job_id = client.get("/api/jobs").json()["items"][0]["id"]
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert "Swift" in detail["description"] and detail["required_skills"]
    assert client.get("/api/jobs/9999").status_code == 404
    assert client.post("/api/jobs/9999/save").status_code == 404


def test_search_twice_creates_no_duplicates(client):
    client.post("/api/jobs/search")
    second = client.post("/api/jobs/search").json()
    assert second["new"] == 0 and second["already_known"] == 3
    assert client.get("/api/jobs/stats").json()["found"] == 3


def test_search_profile_defaults_and_roundtrip(client):
    default = client.get("/api/search-profile").json()
    assert "iOS Engineer" in default["target_roles"] and default["companies"]["ashby"]
    updated = dict(default, minimum_score=85, companies={"greenhouse": ["figma"]})
    assert client.put("/api/search-profile", json=updated).json()["minimum_score"] == 85
    again = client.get("/api/search-profile").json()
    assert again["minimum_score"] == 85 and again["companies"] == {"greenhouse": ["figma"]}


def test_search_profile_rejects_bad_input(client):
    assert client.put("/api/search-profile", json={"companies": {"greenhouse": ["bad slug/../x"]}}).status_code == 422
    assert client.put("/api/search-profile", json={"companies": {"workday": ["x"]}}).status_code == 422
    assert client.put("/api/search-profile", json={"minimum_score": 150}).status_code == 422
