import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(title="ApplyOS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def ollama_up() -> bool:
    try:
        return httpx.get(settings.ollama_base_url, timeout=1.5).status_code == 200
    except Exception:
        return False

@app.get("/api/health")
def health():
    return {
        "backend": True,
        "database": False,   # becomes a real check in Phase 2
        "groq": bool(settings.groq_api_key),  # key present, not yet verified
        "ollama": ollama_up(),
        "playwright": False,  # Phase 10
    }