import logging
import time

from pydantic import BaseModel

from app.ai.base import (
    AIError,
    AIInvalidOutputError,
    AIProvider,
    AIRateLimitError,
    AIResult,
    AIUnavailableError,
)
from app.ai.groq import GroqProvider
from app.ai.ollama import OllamaProvider
from app.config import settings

logger = logging.getLogger("applyos.ai")


class AIRouter:
    """Tries providers in order. A provider that fails is left alone for a cooldown."""

    def __init__(self, providers=None, cooldown_seconds: int | None = None, clock=time.monotonic):
        if providers is None:
            groq, ollama = GroqProvider(), OllamaProvider()
            providers = [ollama, groq] if settings.ai_provider == "ollama" else [groq, ollama]
        self.providers: list[AIProvider] = providers
        self.cooldown_seconds = (
            settings.ai_cooldown_seconds if cooldown_seconds is None else cooldown_seconds
        )
        self.clock = clock
        self._cooldown_until: dict[str, float] = {}

    def _cooldown_left(self, provider: AIProvider) -> float:
        return max(0.0, self._cooldown_until.get(provider.name, 0.0) - self.clock())

    def _cool_down(self, provider: AIProvider, seconds: float | None = None) -> None:
        pause = self.cooldown_seconds if seconds is None else seconds
        self._cooldown_until[provider.name] = self.clock() + pause

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        tier: str = "strong",
    ) -> AIResult:
        invalid_output = False
        for provider in self.providers:
            if not provider.is_configured() or self._cooldown_left(provider) > 0:
                continue
            try:
                return provider.generate(prompt, schema, system=system, tier=tier)
            except AIRateLimitError as exc:
                logger.warning("%s rate limited; pausing it and trying the next provider", provider.name)
                self._cool_down(provider, exc.retry_after)
            except AIInvalidOutputError:
                logger.warning("%s returned invalid output after retries", provider.name)
                invalid_output = True
            except AIError as exc:  # unavailable, key rejected, other request failure
                logger.warning("%s failed: %s", provider.name, exc)
                self._cool_down(provider)
        if invalid_output:
            raise AIInvalidOutputError("AI output stayed invalid: needs human review")
        raise AIUnavailableError("no AI provider available (not configured, cooling down, or failing)")

    def status(self) -> dict:
        return {
            "providers": [
                {
                    "name": provider.name,
                    "configured": provider.is_configured(),
                    "cooldown_seconds": round(self._cooldown_left(provider)),
                }
                for provider in self.providers
            ]
        }


ai_router = AIRouter()
