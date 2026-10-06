import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.base import (
    AIInvalidOutputError,
    AIProvider,
    AIRateLimitError,
    AIResult,
    AIUnavailableError,
    parse_output,
)
from app.ai.groq import GroqProvider
from app.ai.ollama import OllamaProvider
from app.ai.router import AIRouter


class Answer(BaseModel):
    answer: str


# ---------- helpers ----------


def groq_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def make_groq(handler, **overrides) -> GroqProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    options = {
        "api_key": "test-key",
        "primary_model": "primary-model",
        "fallback_model": "fast-model",
        "max_retries": 3,
        "client": client,
    }
    options.update(overrides)
    return GroqProvider(**options)


def make_ollama(handler, **overrides) -> OllamaProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    options = {
        "base_url": "http://localhost:11434",
        "model": "local-model",
        "max_retries": 3,
        "client": client,
    }
    options.update(overrides)
    return OllamaProvider(**options)


class FakeProvider(AIProvider):
    """Scripted provider for router tests. An outcome is a string (success) or an exception."""

    def __init__(self, name, outcomes, configured=True):
        super().__init__(max_retries=1)
        self.name = name
        self.outcomes = list(outcomes)
        self.configured = configured
        self.calls = 0

    def is_configured(self):
        return self.configured

    def complete(self, prompt, schema, system, tier):
        raise NotImplementedError

    def generate(self, prompt, schema, system=None, tier="strong"):
        self.calls += 1
        outcome = self.outcomes[min(self.calls - 1, len(self.outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return AIResult(data=Answer(answer=outcome), provider=self.name, model="fake")


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


# ---------- output parsing ----------


def test_parse_plain_json():
    assert parse_output('{"answer": "hi"}', Answer).answer == "hi"


def test_parse_strips_code_fence():
    assert parse_output('```json\n{"answer": "hi"}\n```', Answer).answer == "hi"


def test_parse_rejects_garbage():
    with pytest.raises(AIInvalidOutputError):
        parse_output("sorry, I cannot do that", Answer)


def test_parse_rejects_wrong_shape():
    with pytest.raises(AIInvalidOutputError):
        parse_output('{"wrong": 1}', Answer)


# ---------- Groq ----------


def test_groq_success_uses_key_and_tier_model():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return groq_reply('{"answer": "pong"}')

    result = make_groq(handler).generate("ping", Answer, tier="fast")
    assert result.data.answer == "pong"
    assert result.provider == "groq"
    assert result.model == "fast-model"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "fast-model"


def test_groq_rate_limit_carries_retry_after():
    def handler(request):
        return httpx.Response(429, headers={"retry-after": "7"})

    with pytest.raises(AIRateLimitError) as info:
        make_groq(handler).generate("ping", Answer)
    assert info.value.retry_after == 7.0


def test_groq_server_error_is_unavailable():
    with pytest.raises(AIUnavailableError):
        make_groq(lambda request: httpx.Response(503)).generate("ping", Answer)


def test_groq_rejected_key_is_unavailable():
    with pytest.raises(AIUnavailableError):
        make_groq(lambda request: httpx.Response(401)).generate("ping", Answer)


def test_groq_timeout_is_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("too slow")

    with pytest.raises(AIUnavailableError):
        make_groq(handler).generate("ping", Answer)


def test_groq_gives_up_after_max_retries():
    calls = []

    def handler(request):
        calls.append(1)
        return groq_reply("this is not json")

    with pytest.raises(AIInvalidOutputError):
        make_groq(handler).generate("ping", Answer)
    assert len(calls) == 3


def test_groq_recovers_on_second_attempt():
    replies = iter(["oops", '{"answer": "fixed"}'])

    def handler(request):
        return groq_reply(next(replies))

    assert make_groq(handler).generate("ping", Answer).data.answer == "fixed"


# ---------- Ollama ----------


def test_ollama_success_sends_schema():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"answer": "pong"}'}})

    result = make_ollama(handler).generate("ping", Answer)
    assert result.provider == "ollama"
    assert result.model == "local-model"
    assert seen["path"] == "/api/chat"
    assert seen["body"]["stream"] is False
    assert "properties" in seen["body"]["format"]


def test_ollama_needs_a_model_name():
    provider = OllamaProvider(base_url="http://localhost:11434", model="")
    assert provider.is_configured() is False


def test_ollama_unreachable_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(AIUnavailableError):
        make_ollama(handler).generate("ping", Answer)


# ---------- router ----------


def test_router_uses_primary_when_it_works():
    groq, ollama = FakeProvider("groq", ["from-groq"]), FakeProvider("ollama", ["from-ollama"])
    result = AIRouter(providers=[groq, ollama]).generate("x", Answer)
    assert result.data.answer == "from-groq"
    assert ollama.calls == 0


def test_router_falls_back_on_rate_limit_and_skips_primary_during_cooldown():
    groq = FakeProvider("groq", [AIRateLimitError("limit")])
    ollama = FakeProvider("ollama", ["from-ollama"])
    router = AIRouter(providers=[groq, ollama], cooldown_seconds=60, clock=Clock())
    assert router.generate("x", Answer).data.answer == "from-ollama"
    assert router.generate("x", Answer).data.answer == "from-ollama"
    assert groq.calls == 1  # not hammered the second time
    assert ollama.calls == 2


def test_router_retries_primary_after_cooldown():
    clock = Clock()
    groq = FakeProvider("groq", [AIRateLimitError("limit"), "groq-is-back"])
    ollama = FakeProvider("ollama", ["from-ollama"])
    router = AIRouter(providers=[groq, ollama], cooldown_seconds=60, clock=clock)
    router.generate("x", Answer)
    clock.now += 61
    assert router.generate("x", Answer).data.answer == "groq-is-back"


def test_router_honors_retry_after():
    clock = Clock()
    groq = FakeProvider("groq", [AIRateLimitError("limit", retry_after=120), "groq-is-back"])
    ollama = FakeProvider("ollama", ["from-ollama"])
    router = AIRouter(providers=[groq, ollama], cooldown_seconds=60, clock=clock)
    router.generate("x", Answer)
    clock.now += 61
    assert router.generate("x", Answer).data.answer == "from-ollama"  # still paused
    clock.now += 60
    assert router.generate("x", Answer).data.answer == "groq-is-back"


def test_router_skips_unconfigured_provider():
    groq = FakeProvider("groq", ["from-groq"], configured=False)
    ollama = FakeProvider("ollama", ["from-ollama"])
    result = AIRouter(providers=[groq, ollama]).generate("x", Answer)
    assert result.data.answer == "from-ollama"
    assert groq.calls == 0


def test_router_nothing_configured():
    groq = FakeProvider("groq", ["a"], configured=False)
    ollama = FakeProvider("ollama", ["b"], configured=False)
    with pytest.raises(AIUnavailableError):
        AIRouter(providers=[groq, ollama]).generate("x", Answer)


def test_router_both_unavailable():
    groq = FakeProvider("groq", [AIUnavailableError("down")])
    ollama = FakeProvider("ollama", [AIUnavailableError("down")])
    with pytest.raises(AIUnavailableError):
        AIRouter(providers=[groq, ollama]).generate("x", Answer)


def test_router_invalid_output_means_human_review():
    groq = FakeProvider("groq", [AIInvalidOutputError("bad json")])
    ollama = FakeProvider("ollama", [AIUnavailableError("down")])
    with pytest.raises(AIInvalidOutputError):
        AIRouter(providers=[groq, ollama]).generate("x", Answer)
