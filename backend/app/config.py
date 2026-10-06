from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = the applyOS folder.
# This file is applyOS/backend/app/config.py, so parents[2] is applyOS.
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/applyos.db"
    ai_provider: str = "groq"  # which provider is tried first: groq or ollama
    ai_max_retries: int = 3  # attempts per provider when the AI returns invalid output
    ai_cooldown_seconds: int = 60  # pause on a provider after a rate limit or outage
    groq_api_key: str = ""
    groq_primary_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "qwen/qwen3.8-27b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    job_score_threshold: int = 80
    require_human_approval: bool = True

    @property
    def resolved_database_url(self) -> str:
        """Turn a relative sqlite path into an absolute one under ROOT_DIR."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            path = Path(self.database_url[len(prefix):])
            if not path.is_absolute():
                path = ROOT_DIR / path
            return f"{prefix}{path}"
        return self.database_url


settings = Settings()
