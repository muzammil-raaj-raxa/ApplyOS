# ApplyOS

Local-first AI job application agent. Finds relevant jobs, scores them against a
verified career profile, and (in later versions) prepares truthful tailored
applications for human approval. Runs on one Mac with no paid services.

## Requirements
- macOS, Python 3.12 or newer, Node.js LTS
- Free Groq API key (optional Ollama for local fallback)

## First-time setup
1. Copy .env.example to .env and add your GROQ_API_KEY
2. Backend: cd backend, python3 -m venv .venv, source .venv/bin/activate, pip install -r requirements.txt
3. Frontend: cd frontend, npm install

## Run
From the project root: ./scripts/start.sh
- Backend: http://localhost:8000
- Dashboard: http://localhost:3000
- Stop both with Ctrl+C

## Database (Phase 2)
SQLite file at data/applyos.db. It is created automatically the first time the
backend starts. The data folder is ignored by Git.

Tables:
- jobs: discovered jobs, with a unique fingerprint to prevent duplicates
- job_scores: AI fit scores per job (model and prompt version stored)
- resumes: generated resume versions per job
- applications: application status and tracking
- application_questions: questions, answers, and approval flags
- interviews: interview rounds and results

Code:
- backend/app/database/database.py: engine, sessions, init_db, check_db
- backend/app/database/models.py: the six tables and the application status list
- backend/app/config.py: settings, with paths resolved from the project root

## Career profile (Phase 3)
The single source of truth about the candidate lives in
backend/app/profile/career_profile.json. It holds contact details, target roles,
experience, education, skills, projects, certifications, preferences, work
authorization and salary policy. The file contains personal data, so Git ignores
it. Keep your own backup copy.

Truthfulness rules (enforced in code):
- A skill may be claimed only if its status is confirmed and it has real
  evidence: professional work, a project, a certification, education, a profile
  link, or an explicit confirmation from the candidate (user_confirmed).
- Evidence marked self_reported (listed but unproven) never counts.
- A resume bullet marked needs_confirmation may only be used through its
  safe_text version, or not at all.
- Bullets may only reference skills that exist in the skills list.
- Dates use YYYY-MM. An empty end date means present.
- Experience length is computed from the dates; the confirmed "3+ years" claim
  is stored in the evidence list.
- Work authorization and sponsorship answers are never auto-submitted. Salary
  policy is ask_every_time.

Code:
- backend/app/profile/validator.py: schema and validation rules
- backend/app/profile/evidence.py: usable skills, gap report, experience months
- backend/app/api/profile.py: GET /api/profile (profile, experience, gaps)

To edit the profile: change career_profile.json in a plain-text editor, then run
the tests. If the file is invalid, /api/profile returns an error that says why.

## AI provider layer (Phase 4)
Every AI call goes through one router in backend/app/ai/. Providers are tried in
order (AI_PROVIDER decides which is first): Groq, then Ollama.

Every reply is checked: JSON parse, Pydantic validation, then retry (up to
AI_MAX_RETRIES per provider). If a provider keeps returning invalid output, the
router tries the other one. If both fail on invalid output, it raises an error
that means "needs human review". Nothing unchecked reaches the database.
Reasoning blocks (<think>...</think>) from reasoning models are removed before
parsing.

Failure handling:
- Rate limit (HTTP 429): that provider is paused. The Retry-After header is
  honored when Groq sends it, otherwise AI_COOLDOWN_SECONDS is used. The router
  moves to the next provider and does not call the paused one again until the
  pause ends.
- Timeout, server error, rejected key: provider paused for AI_COOLDOWN_SECONDS.
- Provider not configured (no key, or no OLLAMA_MODEL): skipped.
- Nothing available: AIUnavailableError, never a silent failure.

Model tiers: tier "strong" (resume tailoring, job evaluation) uses
GROQ_PRIMARY_MODEL. Tier "fast" (classification, simple extraction) uses
GROQ_FALLBACK_MODEL. Ollama uses OLLAMA_MODEL for both. No Ollama model is
hard-coded.

Code:
- backend/app/ai/base.py: provider interface, error types, parse and validate
- backend/app/ai/groq.py: Groq chat completions (key stays in the backend)
- backend/app/ai/ollama.py: local Ollama chat API with schema-enforced output
- backend/app/ai/router.py: fallback order and cooldowns
- backend/app/ai/smoke.py: live check, run: python -m app.ai.smoke
- backend/app/api/ai.py: GET /api/ai/status (configured and cooldown, no keys)

### Local AI with Ollama (optional fallback)
  brew install ollama
  brew services start ollama
  ollama pull qwen3:4b
Then set OLLAMA_MODEL=qwen3:4b in .env. Pick a smaller or larger model to match
your Mac's memory. To test the fallback without touching your Groq key:
  cd backend && source .venv/bin/activate
  GROQ_API_KEY= python -m app.ai.smoke

## Job discovery (Phase 5)
Pipeline: search sources -> normalize -> remove duplicates -> deterministic
filters -> save. No AI is used in this phase.

Sources (independent adapters in backend/app/jobs/sources/): Greenhouse, Lever
and Ashby, using each site's public job board API. Every request sends a
User-Agent and pauses afterwards. HTTP 429 stops that source for the run and is
never retried. A wrong company slug or a failing site is reported in the run's
errors and never stops the other companies or sources.

Search profile: edit it with GET/PUT /api/search-profile (saved to
data/search_profile.json; defaults live in code). Companies are board slugs per
source: boards.greenhouse.io/stripe -> stripe, jobs.lever.co/spotify -> spotify,
jobs.ashbyhq.com/ramp -> ramp. The default company lists are starting points
only. A 404 error means the slug is wrong.

Normalization (backend/app/jobs/normalization.py): clean text, workplace
(remote, hybrid, onsite), salary, employment type, minimum years of experience,
sponsorship, and required versus preferred skills. These are text heuristics.
The original posting link is always kept.

Duplicates: a fingerprint (company + title + canonical URL) catches the same job
seen again. A near-identical job from a different source (same company, similar
title, compatible location) is also dropped. Several openings with the same
title on one source stay separate.

Filters (backend/app/jobs/filtering.py), checked before any AI call. Each match
is stored as a reason on the job. Nothing is silently dropped: filtered jobs stay
in the database and are hidden from the default list.
- unrelated role, or Android-only
- seniority too high (staff, principal, director and similar titles, your
  exclude keywords, or a job asking 4 or more years above your profile)
- remote role limited to a region such as the US or EU
- remote, hybrid or onsite turned off in your career profile preferences
- posting appears closed
- employment type not in your search profile
A missing preferred skill never rejects a job.

Endpoints:
- POST /api/jobs/search: run discovery now, returns counts and errors
- GET /api/jobs: relevant jobs (filters: q, source, company, workplace, decision,
  include_filtered, limit, offset)
- GET /api/jobs/stats and GET /api/jobs/{id}
- POST /api/jobs/{id}/save, POST /api/jobs/{id}/reject, DELETE /api/jobs/{id}/decision
- GET/PUT /api/search-profile

Live check without saving anything (needs internet):
  cd backend && source .venv/bin/activate
  python -m app.jobs.smoke

## Health check
http://localhost:8000/api/health reports backend, database, groq, ollama and
playwright. The database flag runs a real query. The groq flag only checks that
a key is set. The ollama flag is true only when Ollama is running AND the model
in OLLAMA_MODEL is installed. The playwright flag stays false until Phase 10.

## Tests
From the backend folder, with the virtual environment active:
  python -m pytest -v
Currently 111 tests: 5 for the database, 16 for the career profile, 30 for the
AI layer (output parsing, Groq errors, Ollama, readiness check, router fallback
and cooldowns) and 60 for job discovery (normalization, duplicates, filters,
the three sources, the discovery run, and the jobs API). Tests use fake HTTP
responses, so they need no key, no internet and no Ollama.

## Status
- Phase 1 (skeleton): done
- Phase 2 (database): done
- Phase 3 (career profile): done
- Phase 4 (AI provider layer): done
- Phase 5 (job discovery): done
- Phase 6 (job analysis and scoring): next
