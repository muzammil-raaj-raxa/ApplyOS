"""Live check: fetch jobs from the real sites WITHOUT saving anything.
Run from the backend folder: python -m app.jobs.smoke"""
from app.jobs.filtering import filter_job
from app.jobs.normalization import normalize
from app.jobs.search_profile import load_search_profile
from app.jobs.sources.ashby import AshbySource
from app.jobs.sources.greenhouse import GreenhouseSource
from app.jobs.sources.lever import LeverSource


def main() -> None:
    search = load_search_profile()
    for source in (GreenhouseSource(), LeverSource(), AshbySource()):
        slugs = source.slugs(search)
        print(f"\n{source.name}: checking {len(slugs)} companies {slugs}")
        result = source.search(search)
        relevant = []
        for raw in result.jobs:
            try:
                job = normalize(raw)
            except ValueError:
                continue
            if filter_job(job, search).passed:
                relevant.append(job)
        print(f"  fetched {len(result.jobs)} jobs, {len(relevant)} look relevant, {len(result.errors)} errors")
        for error in result.errors:
            print(f"  ERROR {error}")
        for job in relevant[:5]:
            print(f"  - {job.title} @ {job.company} [{job.workplace}] {job.location or ''}")


if __name__ == "__main__":
    main()
