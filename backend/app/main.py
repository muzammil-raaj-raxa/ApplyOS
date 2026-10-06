from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import profile as profile_api
from app.config import settings
from app.database.database import check_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ApplyOS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_api.router)


def ollama_up() -> bool:
    try:
        return httpx.get(settings.ollama_base_url, timeout=1.5).status_code == 200
    except Exception:
        return False


@app.get("/api/health")
def health():
    return {
        "backend": True,
        "database": check_db(),
        "groq": bool(settings.groq_api_key),  # key present, not yet verified
        "ollama": ollama_up(),
        "playwright": False,  # Phase 10
    }
