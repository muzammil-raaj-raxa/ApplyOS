import httpx
from pydantic import BaseModel

from app.ai.base import parse_output
from app.ai.groq import GroqProvider
from app.ai.ollama import OllamaProvider
from app.ai.router import AIRouter


class Answer(BaseModel):
    answer: str


def test_parse_ignores_think_block_with_braces_inside():
    raw = '<think>maybe {"answer": "wrong"} or not</think>\n{"answer": "right"}'
    assert parse_output(raw, Answer).answer == "right"


def test_parse_ignores_multiline_think_block():
    raw = '<think>\nline one\nline two {\n</think>{"answer": "ok"}'
    assert parse_output(raw, Answer).answer == "ok"


def make_ollama(handler, model="qwen3:4b"):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OllamaProvider(base_url="http://localhost:11434", model=model, client=client)


def tags(*names):
    return httpx.Response(200, json={"models": [{"name": n, "model": n} for n in names]})


def test_ready_when_model_is_installed():
    assert make_ollama(lambda request: tags("qwen3:4b", "llama3.2:3b")).is_ready() is True


def test_ready_accepts_latest_tag():
    assert make_ollama(lambda request: tags("llama3:latest"), model="llama3").is_ready() is True


def test_not_ready_when_model_is_missing():
    assert make_ollama(lambda request: tags("llama3.2:3b")).is_ready() is False


def test_not_ready_when_ollama_is_not_running():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    assert make_ollama(handler).is_ready() is False


def test_not_ready_without_a_model_name_and_makes_no_request():
    calls = []

    def handler(request):
        calls.append(request)
        return tags("qwen3:4b")

    assert make_ollama(handler, model="").is_ready() is False
    assert calls == []


def test_router_finds_provider_by_name():
    groq = GroqProvider(api_key="", client=httpx.Client())
    ollama = make_ollama(lambda request: tags())
    router = AIRouter(providers=[groq, ollama])
    assert router.provider("ollama") is ollama
    assert router.provider("groq") is groq
    assert router.provider("nope") is None
