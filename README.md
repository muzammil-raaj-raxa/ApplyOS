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
  ollama pull qwen3:8b
Then set OLLAMA_MODEL=qwen3:8b in .env. Pick a smaller or larger model to match
your Mac's memory. To test the fallback without touching your Groq key:
  cd backend && source .venv/bin/activate
  GROQ_API_KEY= python -m app.ai.smoke

## Health check
http://localhost:8000/api/health reports backend, database, groq, ollama and
playwright. The database flag runs a real query. The groq flag only checks that
a key is set. The playwright flag stays false until Phase 10.

## Tests
From the backend folder, with the virtual environment active:
  python -m pytest -v
Currently 43 tests: 5 for the database, 16 for the career profile (schema
rules, evidence rules, experience months, gap report, and the profile API) and
22 for the AI layer (output parsing, Groq errors, Ollama, router fallback and
cooldowns). AI tests use fake HTTP responses, so they need no key, no internet
and no Ollama.

## Status
- Phase 1 (skeleton): done
- Phase 2 (database): done
- Phase 3 (career profile): done
- Phase 4 (AI provider layer): done
- Phase 5 (job discovery): next
