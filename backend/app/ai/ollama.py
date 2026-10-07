import httpx
from pydantic import BaseModel

from app.ai.base import (
    AIInvalidOutputError,
    AIProvider,
    AIUnavailableError,
    build_messages,
)
from app.config import settings


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        timeout: float = 180.0,  # local models can be slow
        client: httpx.Client | None = None,
    ):
        super().__init__(max_retries)
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = settings.ollama_model if model is None else model
        self.timeout = timeout
        self.client = client or httpx.Client()

    def is_configured(self) -> bool:
        return bool(self.model)  # no hard-coded model: OLLAMA_MODEL must be set

    def is_ready(self) -> bool:
        """True only if Ollama is running AND the configured model is installed."""
        if not self.is_configured():
            return False
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            if response.status_code != 200:
                return False
            installed = set()
            for item in response.json().get("models", []):
                installed.add(item.get("name", ""))
                installed.add(item.get("model", ""))
        except (httpx.HTTPError, ValueError, AttributeError):
            return False
        return self.model in installed or f"{self.model}:latest" in installed

    def complete(
        self, prompt: str, schema: type[BaseModel], system: str | None, tier: str
    ) -> tuple[str, str]:
        payload = {
            "model": self.model,
            "messages": build_messages(prompt, schema, system),
            "stream": False,
            "format": schema.model_json_schema(),  # Ollama enforces the schema
            "options": {"temperature": 0.2},
        }
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
        except httpx.HTTPError as exc:
            raise AIUnavailableError(f"Ollama unreachable: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise AIUnavailableError(
                f"Ollama returned status {response.status_code} (is the model pulled?)"
            )
        try:
            return response.json()["message"]["content"], self.model
        except (ValueError, KeyError, TypeError) as exc:
            raise AIInvalidOutputError("unexpected Ollama response shape") from exc
