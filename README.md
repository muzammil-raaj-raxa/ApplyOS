# ApplyOS

Local-first AI job application agent. Finds relevant jobs, scores them against a
verified career profile, and (in later versions) prepares truthful tailored
applications for human approval. Runs on one Mac with no paid services.

## Requirements
- macOS, Python 3.12+, Node.js LTS
- Free Groq API key (optional Ollama for local fallback)

## First-time setup
1. Copy .env.example to .env and add your GROQ_API_KEY
2. Backend: cd backend, python3.12 -m venv .venv, source .venv/bin/activate, pip install -r requirements.txt
3. Frontend: cd frontend, npm install

## Run
From the project root: ./scripts/start.sh
- Backend: http://localhost:8000
- Dashboard: http://localhost:3000

## Status
Phase 1 (skeleton) done. Phase 2 (database) in progress.
