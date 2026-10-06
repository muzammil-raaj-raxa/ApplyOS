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

## Health check
http://localhost:8000/api/health reports backend, database, groq, ollama and
playwright. The database flag runs a real query. The groq flag only checks that
a key is set. The playwright flag stays false until Phase 10.

## Tests
From the backend folder, with the virtual environment active:
  python -m pytest -v
Currently 21 tests: 5 for the database and 16 for the career profile (schema
rules, evidence rules, experience months, gap report, and the profile API).

## Status
- Phase 1 (skeleton): done
- Phase 2 (database): done
- Phase 3 (career profile): done
- Phase 4 (AI provider layer): next
