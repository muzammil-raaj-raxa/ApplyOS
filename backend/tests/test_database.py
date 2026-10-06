import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import models
from app.database.database import Base, make_engine


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()


def make_job(**overrides):
    data = {
        "source": "greenhouse",
        "title": "iOS Engineer",
        "company": "Acme",
        "url": "https://example.com/jobs/1",
        "description": "Build iOS apps with Swift and SwiftUI.",
        "fingerprint": "fp-1",
    }
    data.update(overrides)
    return models.Job(**data)


def make_score(**overrides):
    data = {"overall_score": 85, "model": "test-model", "prompt_version": "job_analysis_v1"}
    data.update(overrides)
    return models.JobScore(**data)


def test_create_and_read_job(session):
    session.add(make_job())
    session.commit()
    job = session.query(models.Job).one()
    assert job.title == "iOS Engineer"
    assert job.created_at is not None
    assert job.remote is None


def test_duplicate_fingerprint_rejected(session):
    session.add(make_job())
    session.commit()
    session.add(make_job(url="https://example.com/jobs/2"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_score_requires_existing_job(session):
    session.add(make_score(job_id=999))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_deleting_job_removes_scores(session):
    job = make_job()
    job.scores.append(make_score())
    session.add(job)
    session.commit()
    session.delete(job)
    session.commit()
    assert session.query(models.JobScore).count() == 0


def test_application_defaults(session):
    job = make_job()
    session.add(job)
    session.commit()
    application = models.Application(job_id=job.id, application_url=job.url)
    session.add(application)
    session.commit()
    assert application.status == models.ApplicationStatus.DISCOVERED.value
    question = models.ApplicationQuestion(
        application_id=application.id, question="Why us?", question_type="motivation"
    )
    session.add(question)
    session.commit()
    assert question.requires_human is False
    assert question.confidence == 0.0
