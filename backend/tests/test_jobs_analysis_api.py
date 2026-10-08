import pytest
from analysis_helpers import CallbackProvider, add_job, good_reply, make_profile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.ai.base import AIUnavailableError
from app.ai.router import AIRouter
from app.api import jobs as jobs_api
from app.database.database import Base, get_db, make_engine
from app.jobs import search_profile as search_profile_module


class Env:
    """Test environment: an in-memory database, a scripted AI, and a way to seed jobs."""

    def __init__(self, tmp_path, monkeypatch):
        engine = make_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.factory = sessionmaker(bind=engine)
        self.reply = lambda prompt, n: good_reply()
        self.provider = CallbackProvider(lambda prompt, n: self.reply(prompt, n))
        self.router = AIRouter(providers=[self.provider])

        def override_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        monkeypatch.setattr(search_profile_module, "SEARCH_PROFILE_PATH", tmp_path / "search_profile.json")
        monkeypatch.setattr(jobs_api, "load_profile", lambda: make_profile())
        monkeypatch.setattr(jobs_api.settings, "ai_batch_pause_seconds", 0.0)
        app = FastAPI()
        app.include_router(jobs_api.router)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[jobs_api.get_router] = lambda: self.router
        self.client = TestClient(app)

    def seed(self, **kwargs) -> int:
        db = self.factory()
        job = add_job(db, **kwargs)
        job_id = job.id
        db.close()
        return job_id


@pytest.fixture()
def env(tmp_path, monkeypatch):
    return Env(tmp_path, monkeypatch)


def test_analyze_one_job_and_see_it_in_detail_and_list(env):
    job_id = env.seed()
    response = env.client.post(f"/api/jobs/{job_id}/analyze")
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True and body["analysis"]["overall_score"] == 91

    detail = env.client.get(f"/api/jobs/{job_id}").json()
    assert detail["analysis"]["recommendation"] == "APPLY"
    assert detail["score"]["overall_score"] == 91 and detail["score"]["priority"] == "HIGH"
    assert detail["score"]["matched"] == ["iOS", "Swift", "UIKit"] and detail["score"]["gaps"] == ["CI/CD"]

    item = env.client.get("/api/jobs").json()["items"][0]
    assert item["score"]["overall_score"] == 91 and item["analysis_status"] is None


def test_analyze_again_reuses_result_unless_forced(env):
    job_id = env.seed()
    env.client.post(f"/api/jobs/{job_id}/analyze")
    assert env.client.post(f"/api/jobs/{job_id}/analyze").json()["created"] is False
    assert env.client.post(f"/api/jobs/{job_id}/analyze", params={"force": True}).json()["created"] is True
    assert len(env.provider.prompts) == 2


def test_ai_unavailable_returns_503(env):
    job_id = env.seed()

    def down(prompt, n):
        raise AIUnavailableError("down")

    env.reply = down
    response = env.client.post(f"/api/jobs/{job_id}/analyze")
    assert response.status_code == 503
    assert env.client.get(f"/api/jobs/{job_id}").json()["score"] is None


def test_failed_validation_returns_422_and_marks_needs_review(env):
    job_id = env.seed()
    env.reply = lambda prompt, n: good_reply(ref="Kotlin")
    response = env.client.post(f"/api/jobs/{job_id}/analyze")
    assert response.status_code == 422 and "needs_review" in response.json()["detail"]
    detail = env.client.get(f"/api/jobs/{job_id}").json()
    assert detail["analysis_status"] == "needs_review" and detail["analysis_error"]


def test_unknown_job_is_404_and_bad_profile_is_409(env, monkeypatch):
    assert env.client.post("/api/jobs/999/analyze").status_code == 404
    job_id = env.seed()

    def broken():
        raise ValueError("profile is invalid")

    monkeypatch.setattr(jobs_api, "load_profile", broken)
    assert env.client.post(f"/api/jobs/{job_id}/analyze").status_code == 409
    assert env.client.post("/api/jobs/analyze").status_code == 409


def test_batch_endpoint_scores_jobs_and_reports_the_rest(env):
    for n in range(1, 4):
        env.seed(n=n)
    summary = env.client.post("/api/jobs/analyze", params={"limit": 2}).json()
    assert summary["analyzed"] == 2 and summary["pending"] == 1 and summary["stopped_reason"] is None
    assert env.client.post("/api/jobs/analyze", params={"limit": 2}).json()["analyzed"] == 1


def test_list_can_filter_and_sort_by_score(env):
    low = env.seed(n=1, title="iOS Engineer", required=("Swift", "Kotlin", "GraphQL", "Android"))
    high = env.seed(n=2, title="Mobile Engineer")
    env.seed(n=3, title="Swift Developer")  # never analyzed

    env.reply = lambda prompt, n: good_reply(technical=40 if "Title: iOS Engineer" in prompt else 95, ref="Swift")
    env.client.post(f"/api/jobs/{low}/analyze")
    env.client.post(f"/api/jobs/{high}/analyze")

    ranked = env.client.get("/api/jobs", params={"sort": "score"}).json()["items"]
    assert [item["id"] for item in ranked][:2] == [high, low]
    assert ranked[2]["score"] is None  # unscored jobs sort last

    assert env.client.get("/api/jobs", params={"min_score": 85}).json()["total"] == 1
    assert env.client.get("/api/jobs", params={"scored": True}).json()["total"] == 2
    assert env.client.get("/api/jobs", params={"scored": False}).json()["total"] == 1


def test_stats_count_analyzed_and_high_fit_jobs(env):
    strong = env.seed(n=1)
    weak = env.seed(n=2, title="Mobile Engineer", required=("Swift", "Kotlin", "GraphQL", "Android"))
    env.reply = lambda prompt, n: good_reply(technical=10 if "Title: Mobile Engineer" in prompt else 95)
    env.client.post(f"/api/jobs/{strong}/analyze")
    env.client.post(f"/api/jobs/{weak}/analyze")
    stats = env.client.get("/api/jobs/stats").json()
    assert stats["analyzed"] == 2 and stats["high_fit"] == 1  # default minimum score is 80


def test_high_fit_uses_only_the_latest_analysis(env):
    job_id = env.seed(required=("Swift", "UIKit"))  # fewer than 3 required: no keyword cross-check
    env.client.post(f"/api/jobs/{job_id}/analyze")  # 91
    env.reply = lambda prompt, n: good_reply(technical=10)
    env.client.post(f"/api/jobs/{job_id}/analyze", params={"force": True})
    stats = env.client.get("/api/jobs/stats").json()
    assert stats["analyzed"] == 1 and stats["high_fit"] == 0
