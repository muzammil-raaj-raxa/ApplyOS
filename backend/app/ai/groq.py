import httpx
from pydantic import BaseModel

from app.ai.base import (
    AIError,
    AIInvalidOutputError,
    AIProvider,
    AIRateLimitError,
    AIUnavailableError,
    build_messages,
)
from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        primary_model: str | None = None,
        fallback_model: str | None = None,
        max_retries: int | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        super().__init__(max_retries)
        self.api_key = settings.groq_api_key if api_key is None else api_key
        self.primary_model = primary_model or settings.groq_primary_model
        self.fallback_model = fallback_model or settings.groq_fallback_model
        self.timeout = timeout
        self.client = client or httpx.Client()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def complete(
        self, prompt: str, schema: type[BaseModel], system: str | None, tier: str
    ) -> tuple[str, str]:
        model = self.primary_model if tier == "strong" else self.fallback_model
        payload = {
            "model": model,
            "messages": build_messages(prompt, schema, system),
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = self.client.post(
                GROQ_URL, json=payload, headers=headers, timeout=self.timeout
            )
        except httpx.HTTPError as exc:
            raise AIUnavailableError(f"Groq unreachable: {type(exc).__name__}") from exc

        if response.status_code == 429:
            try:
                retry_after = float(response.headers.get("retry-after", ""))
            except ValueError:
                retry_after = None
            raise AIRateLimitError("Groq rate limit reached", retry_after=retry_after)
        if response.status_code in (401, 403):
            raise AIUnavailableError("Groq rejected the API key")
        if response.status_code >= 500:
            raise AIUnavailableError(f"Groq server error {response.status_code}")
        if response.status_code != 200:
            raise AIError(f"Groq request failed with status {response.status_code}")

        try:
            return response.json()["choices"][0]["message"]["content"], model
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIInvalidOutputError("unexpected Groq response shape") from exc
