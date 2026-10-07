from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.router import ai_router
from app.api import ai as ai_api
from app.api import jobs as jobs_api
from app.api import profile as profile_api
from app.api import search_profile as search_profile_api
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
app.include_router(ai_api.router)
app.include_router(jobs_api.router)
app.include_router(search_profile_api.router)


@app.get("/api/health")
def health():
    groq = ai_router.provider("groq")
    ollama = ai_router.provider("ollama")
    return {
        "backend": True,
        "database": check_db(),
        "groq": bool(groq and groq.is_configured()),  # key present, not yet verified
        "ollama": bool(ollama and ollama.is_ready()),  # running AND model installed
        "playwright": False,  # Phase 10
    }
