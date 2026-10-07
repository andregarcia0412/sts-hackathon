from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ai_microservice.config import Settings
from ai_microservice.llm import LLMClient, LLMError


class Answer(BaseModel):
    value: int


class FakeOllama:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.requests: list[dict] = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.contents.pop(0)))


def make_client(contents: list[str], **settings) -> tuple[LLMClient, FakeOllama]:
    fake = FakeOllama(contents)
    config = Settings(_env_file=None, ollama_model="base-model", **settings)
    return LLMClient(config, chat_client=fake, web_client=fake), fake


async def test_structured_sends_json_schema_and_parses():
    client, fake = make_client(['{"value": 42}'])
    result = await client.structured([{"role": "user", "content": "?"}], Answer)
    assert result == Answer(value=42)
    assert fake.requests[0]["format"] == Answer.model_json_schema()
    assert fake.requests[0]["model"] == "base-model"


async def test_structured_retries_once_feeding_back_the_error():
    client, fake = make_client(['{"value": "x"}', '{"value": 7}'])
    result = await client.structured([{"role": "user", "content": "?"}], Answer)
    assert result.value == 7
    retry_messages = fake.requests[1]["messages"]
    assert retry_messages[-2] == {"role": "assistant", "content": '{"value": "x"}'}
    assert "schema" in retry_messages[-1]["content"]


async def test_structured_gives_up_after_second_invalid_answer():
    client, _ = make_client(["nope", "still nope"])
    with pytest.raises(LLMError):
        await client.structured([{"role": "user", "content": "?"}], Answer)


async def test_role_override_selects_model():
    client, fake = make_client(['{"value": 1}'], ollama_model_judge="judge-model")
    await client.structured([{"role": "user", "content": "?"}], Answer, role="judge")
    assert fake.requests[0]["model"] == "judge-model"


async def test_web_search_requires_api_key():
    client, _ = make_client([])
    with pytest.raises(LLMError):
        await client.web_search("circuit breaker")


def test_missing_model_is_a_clear_error():
    with pytest.raises(RuntimeError, match="OLLAMA_MODEL"):
        Settings(_env_file=None).model_for("default")


def test_cors_origins_accepts_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    assert Settings(_env_file=None).cors_origins == ["http://a.test", "http://b.test"]
