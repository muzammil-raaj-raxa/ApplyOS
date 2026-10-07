from app.jobs.deduplication import (
    DedupIndex,
    canonical_url,
    company_key,
    make_fingerprint,
    title_key,
)
from app.jobs.filtering import filter_job, role_tier
from app.jobs.normalization import normalize
from app.jobs.schemas import RawJob
from app.jobs.search_profile import SearchProfile, default_search_profile
from app.profile.validator import Preferences


def test_company_and_title_keys():
    assert company_key("Stripe, Inc.") == "stripe"
    assert company_key("The Walt Disney Company") == "waltdisneycompany"
    assert title_key("Sr. iOS Engineer (Remote)") == "senior ios engineer"


def test_canonical_url_ignores_tracking_and_case():
    a = canonical_url("http://www.Example.com/jobs/1/?utm_source=x&ref=y")
    b = canonical_url("https://example.com/jobs/1")
    assert a == b
    assert canonical_url("https://example.com/careers?gh_jid=123") != b


def test_fingerprint_is_stable_and_url_sensitive():
    one = make_fingerprint("Stripe, Inc.", "iOS Engineer", "https://x.com/jobs/1?utm_medium=a")
    two = make_fingerprint("stripe", "iOS  Engineer", "https://x.com/jobs/1")
    other = make_fingerprint("stripe", "iOS Engineer", "https://x.com/jobs/2")
    assert one == two
    assert one != other


def add(index, source, company, title, location, url):
    fingerprint = make_fingerprint(company, title, url)
    from app.jobs.deduplication import location_key
    args = (fingerprint, source, company_key(company), title_key(title), location_key(location))
    reason = index.check(*args)
    if reason is None:
        index.add(*args)
    return reason


def test_same_fingerprint_is_a_duplicate():
    index = DedupIndex()
    assert add(index, "greenhouse", "Acme", "iOS Engineer", "Remote", "https://a.com/1") is None
    assert add(index, "greenhouse", "Acme", "iOS Engineer", "Remote", "https://a.com/1") == "already stored"


def test_same_job_on_two_sources_is_a_duplicate():
    index = DedupIndex()
    add(index, "greenhouse", "Acme Inc", "Senior iOS Engineer", "Remote - US", "https://a.com/1")
    reason = add(index, "lever", "Acme", "Sr. iOS Engineer", "Remote", "https://lever.co/acme/2")
    assert reason == "same job already found via greenhouse"


def test_same_source_openings_with_same_title_stay_separate():
    index = DedupIndex()
    add(index, "greenhouse", "Acme", "iOS Engineer", "London", "https://a.com/1")
    assert add(index, "greenhouse", "Acme", "iOS Engineer", "London", "https://a.com/2") is None


def test_different_city_is_not_a_cross_source_duplicate():
    index = DedupIndex()
    add(index, "greenhouse", "Acme", "iOS Engineer", "London", "https://a.com/1")
    assert add(index, "lever", "Acme", "iOS Engineer", "Berlin", "https://lever.co/acme/2") is None


# ---------- filtering ----------


def make_job(title="iOS Engineer", location="Remote - Worldwide", description="Build apps.", **overrides):
    data = {
        "source": "greenhouse", "external_id": "1", "title": title, "company": "Acme",
        "url": "https://a.com/jobs/1", "description": description, "location": location,
    }
    data.update(overrides)
    return normalize(RawJob(**data))


SEARCH = default_search_profile()
PREFS = Preferences(remote=True, hybrid=True, onsite=True, relocation=True)


def reasons(job, **kwargs):
    kwargs.setdefault("candidate_years", 3.0)
    return filter_job(job, SEARCH, PREFS, **kwargs).reasons


def test_good_job_passes():
    result = filter_job(make_job(), SEARCH, PREFS, 3.0)
    assert result.passed and result.role_tier == "primary" and result.reasons == []


def test_role_tiers():
    assert role_tier("Senior iOS Developer") == "primary"
    assert role_tier("Mobile Software Engineer") == "primary"
    assert role_tier("Software Engineer, Payments") == "secondary"
    assert role_tier("Frontend Engineer") == "secondary"
    assert role_tier("Account Executive") == "unrelated"


def test_unrelated_and_android_only_are_rejected():
    assert "unrelated role" in reasons(make_job(title="Account Executive"))
    assert "Android-only role" in reasons(make_job(title="Mobile Engineer (Android)"))
    assert "Android-only role" not in reasons(make_job(title="Mobile Engineer (iOS and Android)"))


def test_too_senior_titles_are_rejected():
    assert any("seniority" in r for r in reasons(make_job(title="Staff iOS Engineer")))
    assert any("seniority" in r for r in reasons(make_job(title="Software Engineer (Principal)")))
    assert reasons(make_job(title="Senior iOS Engineer")) == []


def test_exclude_keywords_from_search_profile():
    search = SearchProfile(exclude_keywords=["Contractor"])
    result = filter_job(make_job(title="iOS Engineer Contractor"), search, PREFS, 3.0)
    assert "title contains excluded keyword 'Contractor'" in result.reasons


def test_years_gap_rejects_only_when_clearly_too_senior():
    assert any("10+ years" in r for r in reasons(make_job(description="10+ years of iOS experience required.")))
    assert reasons(make_job(description="5+ years of iOS experience.")) == []


def test_preferences_can_turn_off_onsite():
    prefs = Preferences(remote=True, hybrid=True, onsite=False, relocation=False)
    job = make_job(location="Berlin", description="This role is on-site.")
    result = filter_job(job, SEARCH, prefs, 3.0)
    assert "onsite roles are turned off in your preferences" in result.reasons


def test_remote_role_limited_to_a_region_is_rejected():
    assert any("limited to" in r for r in reasons(make_job(location="Remote - US")))
    assert any("limited to" in r for r in reasons(make_job(location="United States (Remote)")))
    desc = "This remote position is US-only."
    assert any("limited to" in r for r in reasons(make_job(description=desc, workplace_hint="remote")))
    assert reasons(make_job(location="Remote - Worldwide")) == []
    assert reasons(make_job(location="Remote")) == []


def test_closed_posting_is_rejected():
    job = make_job(description="This position has been filled.")
    assert "application appears to be closed" in reasons(job)


def test_employment_type_must_match_search_profile():
    job = make_job(employment_hint="Contract")
    assert any("employment type" in r for r in reasons(job))
    assert reasons(make_job(employment_hint="FullTime")) == []


def test_missing_preferred_skill_never_rejects():
    jd = "Requirements:\n- Swift\n\nNice to have:\n- Fastlane\n- Kotlin"
    assert reasons(make_job(description=jd)) == []
