import pytest
from pydantic import BaseModel

from app.ai.base import AIInvalidOutputError, AIProvider, AIUnavailableError
from app.ai.router import AIRouter


class Answer(BaseModel):
    answer: str


class ScriptedProvider(AIProvider):
    """Returns scripted raw replies and records every prompt it receives."""

    def __init__(self, name, replies, max_retries=3):
        super().__init__(max_retries=max_retries)
        self.name = name
        self.replies = list(replies)
        self.prompts = []

    def is_configured(self):
        return True

    def complete(self, prompt, schema, system, tier):
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self.replies) - 1)
        return self.replies[index], "scripted-model"


def no_banned_words(result: Answer) -> None:
    if "banned" in result.answer:
        raise ValueError("answer contains a banned word")


def test_failed_check_retries_with_the_reason_then_succeeds():
    provider = ScriptedProvider("groq", ['{"answer": "banned"}', '{"answer": "fine"}'])
    result = provider.generate("p", Answer, check=no_banned_words)
    assert result.data.answer == "fine"
    assert "answer contains a banned word" in provider.prompts[1]


def test_check_that_never_passes_raises_invalid_output():
    provider = ScriptedProvider("groq", ['{"answer": "banned"}'], max_retries=2)
    with pytest.raises(AIInvalidOutputError, match="rule check failed"):
        provider.generate("p", Answer, check=no_banned_words)
    assert len(provider.prompts) == 2


def test_no_check_means_old_behavior():
    provider = ScriptedProvider("groq", ['{"answer": "banned"}'])
    assert provider.generate("p", Answer).data.answer == "banned"


def test_router_falls_back_to_next_provider_when_check_keeps_failing():
    groq = ScriptedProvider("groq", ['{"answer": "banned"}'], max_retries=2)
    ollama = ScriptedProvider("ollama", ['{"answer": "clean"}'])
    result = AIRouter(providers=[groq, ollama]).generate("p", Answer, check=no_banned_words)
    assert (result.provider, result.data.answer) == ("ollama", "clean")


def test_router_human_review_error_includes_the_reason():
    groq = ScriptedProvider("groq", ['{"answer": "banned"}'], max_retries=1)
    ollama = ScriptedProvider("ollama", ['{"answer": "banned"}'], max_retries=1)
    with pytest.raises(AIInvalidOutputError, match="banned word"):
        AIRouter(providers=[groq, ollama]).generate("p", Answer, check=no_banned_words)


def test_router_still_works_without_a_check():
    groq = ScriptedProvider("groq", ['{"answer": "ok"}'])
    assert AIRouter(providers=[groq]).generate("p", Answer).data.answer == "ok"
    with pytest.raises(AIUnavailableError):
        AIRouter(providers=[]).generate("p", Answer)
