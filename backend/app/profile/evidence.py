from datetime import date

from app.profile.validator import CareerProfile


def usable_skills(profile: CareerProfile) -> list[str]:
    """Skills the AI is allowed to claim."""
    return [s.name for s in profile.skills if s.status == "confirmed"]


def skills_needing_evidence(profile: CareerProfile) -> list[str]:
    return [s.name for s in profile.skills if s.status == "needs_evidence"]


def bullets_needing_confirmation(profile: CareerProfile) -> list[dict]:
    items = []
    entries = [(job.company, job.bullets) for job in profile.experience]
    entries += [(project.name, project.bullets) for project in profile.projects]
    for where, bullets in entries:
        for bullet in bullets:
            if bullet.status == "needs_confirmation":
                items.append(
                    {"where": where, "id": bullet.id, "text": bullet.text, "note": bullet.note}
                )
    return items


def missing_fields(profile: CareerProfile) -> list[str]:
    missing = []
    if not profile.work_authorization:
        missing.append("work_authorization")
    if not profile.salary_preferences:
        missing.append("salary_preferences")
    for key, value in profile.candidate.model_dump().items():
        if not value:
            missing.append(f"candidate.{key}")
    return missing


def gap_report(profile: CareerProfile) -> dict:
    return {
        "skills_needing_evidence": skills_needing_evidence(profile),
        "bullets_needing_confirmation": bullets_needing_confirmation(profile),
        "missing_fields": missing_fields(profile),
    }


def _month_index(year_month: str) -> int:
    year, month = year_month.split("-")
    return int(year) * 12 + int(month) - 1


def total_months_of_experience(profile: CareerProfile, today: date | None = None) -> int:
    """Employed months from the dates in the profile. Overlaps count once; both end months count."""
    today = today or date.today()
    now_index = today.year * 12 + today.month - 1
    spans = sorted(
        (_month_index(job.start), _month_index(job.end) if job.end else now_index)
        for job in profile.experience
    )
    total = 0
    current_start = current_end = None
    for start, end in spans:
        if current_end is None or start > current_end:
            if current_end is not None:
                total += current_end - current_start + 1
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_end is not None:
        total += current_end - current_start + 1
    return total
