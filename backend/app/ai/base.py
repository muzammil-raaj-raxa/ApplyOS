import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.config import settings


class AIError(Exception):
    """Base class for every AI failure."""


class AIUnavailableError(AIError):
    """Provider unreachable, timed out, key rejected, or server error."""


class AIRateLimitError(AIError):
    """Provider said slow down (HTTP 429)."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class AIInvalidOutputError(AIError):
    """The AI answered, but not with valid JSON in the expected shape."""


@dataclass
class AIResult:
    data: BaseModel
    provider: str
    model: str


def parse_output(raw: str, schema: type[BaseModel]) -> BaseModel:
    """Raw text -> JSON -> Pydantic. Raises AIInvalidOutputError if either step fails."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()  # reasoning models
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)  # models sometimes add code fences
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise AIInvalidOutputError("no JSON object found in the reply")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIInvalidOutputError(f"reply is not valid JSON: {exc}") from exc
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise AIInvalidOutputError(f"reply does not match the schema: {exc}") from exc


def build_messages(prompt: str, schema: type[BaseModel], system: str | None) -> list[dict]:
    """Chat messages that tell the model to answer with JSON matching the schema."""
    rules = (
        "Return ONLY a JSON object that matches this JSON Schema. "
        "No markdown, no commentary.\n" + json.dumps(schema.model_json_schema())
    )
    system_text = f"{system}\n\n{rules}" if system else rules
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": prompt},
    ]


class AIProvider(ABC):
    """One AI backend. tier is 'strong' (hard tasks) or 'fast' (simple tasks)."""

    name: str

    def __init__(self, max_retries: int | None = None):
        self.max_retries = max(1, max_retries or settings.ai_max_retries)

    @abstractmethod
    def is_configured(self) -> bool:
        """True when this provider has what it needs (key, model name)."""

    @abstractmethod
    def complete(
        self, prompt: str, schema: type[BaseModel], system: str | None, tier: str
    ) -> tuple[str, str]:
        """One request. Returns (raw reply text, model used)."""

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        tier: str = "strong",
        check: Callable[[BaseModel], None] | None = None,
    ) -> AIResult:
        """Ask, validate (JSON, schema, then the optional business-rule check), and retry
        with the rejection reason when the output is invalid. check raises ValueError."""
        last_error: AIInvalidOutputError | None = None
        current = prompt
        for _ in range(self.max_retries):
            raw, model = self.complete(current, schema, system, tier)
            try:
                data = parse_output(raw, schema)
                if check is not None:
                    try:
                        check(data)
                    except ValueError as exc:
                        raise AIInvalidOutputError(f"rule check failed: {exc}") from exc
            except AIInvalidOutputError as exc:
                last_error = exc
                current = (
                    f"{prompt}\n\nYour previous reply was rejected: {exc}\n"
                    "Return ONLY valid JSON that matches the schema."
                )
                continue
            return AIResult(data=data, provider=self.name, model=model)
        raise last_error
