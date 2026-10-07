import pytest

from app.jobs.normalization import (
    detect_employment_type,
    detect_sponsorship,
    detect_workplace,
    extract_min_years,
    extract_salary,
    extract_skills,
    html_to_text,
    normalize,
)
from app.jobs.schemas import RawJob

SAMPLE_JD = """About the role
We build the iOS app used by millions.

Requirements:
- 3+ years of professional iOS development experience
- Strong knowledge of Swift and UIKit
- Experience with REST APIs

Nice to have:
- SwiftUI or Combine experience
- Fastlane and CI/CD
"""


def test_html_to_text_handles_greenhouse_escaped_html():
    escaped = "&lt;p&gt;We are hiring &amp;amp; growing&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Swift&lt;/li&gt;&lt;li&gt;UIKit&lt;/li&gt;&lt;/ul&gt;"
    text = html_to_text(escaped)
    assert "<" not in text
    assert "We are hiring & growing" in text
    assert "- Swift" in text and "- UIKit" in text


def test_html_to_text_keeps_plain_text_and_handles_empty():
    assert html_to_text("Just text") == "Just text"
    assert html_to_text(None) == ""


def test_workplace_hint_wins():
    assert detect_workplace("iOS Engineer", "New York", "", "remote") == "remote"
    assert detect_workplace("iOS Engineer", "New York", "", "on-site") == "onsite"


def test_workplace_from_location_and_description():
    assert detect_workplace("iOS Engineer", "Remote - US", "", None) == "remote"
    assert detect_workplace("iOS Engineer", "London (Hybrid)", "", None) == "hybrid"
    assert detect_workplace("iOS Engineer", "Berlin", "We are remote-first.", None) == "remote"
    assert detect_workplace("iOS Engineer", "Berlin", "Three days a week in the office.", None) == "hybrid"
    assert detect_workplace("iOS Engineer", "Berlin", "We build apps.", None) == "unknown"


def test_salary_ranges():
    assert extract_salary("Pay: $120,000 - $150,000 per year") == (120000, 150000, "USD")
    assert extract_salary("Salary $120k–$150k") == (120000, 150000, "USD")
    assert extract_salary("£70,000 to £90,000") == (70000, 90000, "GBP")
    assert extract_salary("Hourly rate $45 - $60") == (None, None, None)
    assert extract_salary("No pay info here") == (None, None, None)


def test_min_years():
    assert extract_min_years("3+ years of iOS experience") == 3
    assert extract_min_years("5+ years of software experience and 3+ years of iOS experience") == 5
    assert extract_min_years("1-3 years of relevant experience") == 1
    assert extract_min_years("We were founded 10 years ago") is None
    assert extract_min_years("No numbers here") is None


def test_sponsorship():
    assert detect_sponsorship("We are unable to sponsor visas at this time.") == "not_available"
    assert detect_sponsorship("Must be authorized to work in the US.") == "not_available"
    assert detect_sponsorship("Visa sponsorship is available for this role.") == "available"
    assert detect_sponsorship("Great benefits.") == "unknown"


def test_employment_type():
    assert detect_employment_type("FullTime", "iOS Engineer", "") == "full-time"
    assert detect_employment_type(None, "iOS Engineering Intern", "") == "internship"
    assert detect_employment_type("Contract", "iOS Engineer", "") == "contract"
    assert detect_employment_type(None, "iOS Engineer", "") is None


def test_skills_split_required_and_preferred():
    required, preferred = extract_skills("iOS Engineer", SAMPLE_JD)
    assert {"iOS", "Swift", "UIKit", "REST APIs"} <= set(required)
    assert {"SwiftUI", "Combine", "Fastlane", "CI/CD"} <= set(preferred)
    assert not set(required) & set(preferred)


def test_skill_matching_avoids_false_positives():
    required, _ = extract_skills("Engineer", "Experience with SwiftUI and React Native.\nWe move at a swift pace.")
    assert "SwiftUI" in required and "React Native" in required
    assert "Swift" not in required and "React" not in required


def make_raw(**overrides) -> RawJob:
    data = {
        "source": "greenhouse",
        "external_id": "1",
        "title": "  Senior iOS   Engineer ",
        "company": "Stripe, Inc.",
        "url": "https://boards.greenhouse.io/stripe/jobs/1?utm_source=x",
        "description": SAMPLE_JD,
        "location": "Remote - Worldwide",
    }
    data.update(overrides)
    return RawJob(**data)


def test_normalize_end_to_end():
    job = normalize(make_raw())
    assert job.title == "Senior iOS Engineer"
    assert job.workplace == "remote" and job.remote is True
    assert job.company_key == "stripe"
    assert job.requirements["minimum_years"] == 3
    assert "Swift" in job.requirements["required_skills"]
    assert job.requirements["sponsorship"] == "unknown"
    assert job.parsing_error is None
    assert len(job.fingerprint) == 64


def test_normalize_prefers_structured_salary_over_text():
    job = normalize(make_raw(description="Pay $90,000 - $100,000", salary_min=150000, salary_max=180000, salary_currency="USD"))
    assert (job.salary_min, job.salary_max) == (150000, 180000)


def test_normalize_flags_empty_description():
    job = normalize(make_raw(description=""))
    assert job.parsing_error == "empty description"


def test_normalize_rejects_missing_url():
    with pytest.raises(ValueError):
        normalize(make_raw(url=""))
