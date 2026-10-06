#!/bin/bash
cd "$(dirname "$0")/.."

cleanup() {
  echo ""
  echo "Stopping ApplyOS..."
  trap - INT TERM
  kill 0
}
trap cleanup INT TERM

(cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000) &
(cd frontend && npm run dev) &

echo "ApplyOS: backend http://localhost:8000 | dashboard http://localhost:3000"
wait
