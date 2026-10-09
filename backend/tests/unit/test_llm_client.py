from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from backend.config import Settings
from backend.llm.client import LLMClient, LLMError


class Answer(BaseModel):
    value: int


class FakeOllama:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.requests: list[dict] = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        content = self.contents.pop(0)
        if isinstance(content, Exception):
            raise content
        return SimpleNamespace(message=SimpleNamespace(content=content))


def make_client(contents: list, **settings) -> tuple[LLMClient, FakeOllama]:
    fake = FakeOllama(contents)
    config = Settings(_env_file=None, ollama_model="base-model", ollama_retries=1, **settings)
    return LLMClient(config, chat_client=fake, web_client=fake, retry_backoff_s=0), fake


async def test_structured_sends_json_schema_with_temperature_zero():
    client, fake = make_client(['{"value": 42}'])
    result = await client.structured([{"role": "user", "content": "?"}], Answer)
    assert result == Answer(value=42)
    assert fake.requests[0]["format"] == Answer.model_json_schema()
    assert fake.requests[0]["model"] == "base-model"
    assert fake.requests[0]["options"]["temperature"] == 0


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


async def test_transport_errors_are_retried():
    client, fake = make_client([ConnectionError("boom"), '{"value": 3}'])
    assert (await client.structured([{"role": "user", "content": "?"}], Answer)).value == 3
    assert len(fake.requests) == 2


async def test_transport_errors_give_up_after_retries():
    client, _ = make_client([ConnectionError("a"), ConnectionError("b")])
    with pytest.raises(LLMError):
        await client.chat([{"role": "user", "content": "?"}])


async def test_role_override_selects_model():
    client, fake = make_client(['{"value": 1}'], ollama_model_judge="judge-model")
    await client.structured([{"role": "user", "content": "?"}], Answer, role="judge")
    assert fake.requests[0]["model"] == "judge-model"


async def test_web_search_requires_api_key():
    client, _ = make_client([])
    with pytest.raises(LLMError):
        await client.web_search("circuit breaker")


class Nested(BaseModel):
    regra_id: str
    quote: str


class Out(BaseModel):
    evidencias: list[Nested]


async def test_structured_puts_the_schema_in_the_prompt():
    client, fake = make_client(['{"value": 1}'])
    await client.structured([{"role": "system", "content": "sys"}, {"role": "user", "content": "?"}], Answer)
    messages = fake.requests[0]["messages"]
    assert messages[0] == {"role": "system", "content": "sys"}
    assert messages[1]["role"] == "system" and '"value"' in messages[1]["content"]
    assert messages[-1] == {"role": "user", "content": "?"}


@pytest.mark.parametrize("content", ['```json\n{"value": 5}\n```', '```\n{"value": 5}\n```',
                                     'Aqui está:\n{"value": 5}\nFim.'])
async def test_structured_accepts_fenced_or_wrapped_json(content):
    client, fake = make_client([content])
    assert (await client.structured([{"role": "user", "content": "?"}], Answer)).value == 5
    assert len(fake.requests) == 1


async def test_retry_feedback_names_the_expected_fields():
    client, fake = make_client(['{"evidencias": [{"regra": "NOV-D1", "quote": "x"}]}',
                                '{"evidencias": [{"regra_id": "NOV-D1", "quote": "x"}]}'])
    result = await client.structured([{"role": "user", "content": "?"}], Out)
    assert result.evidencias[0].regra_id == "NOV-D1"
    feedback = fake.requests[1]["messages"][-1]["content"]
    assert "evidencias.0.regra_id" in feedback and "regra_id, quote" in feedback


async def test_schema_attempts_are_configurable():
    client, fake = make_client(["a", "b", '{"value": 2}'], ollama_schema_retries=2)
    assert (await client.structured([{"role": "user", "content": "?"}], Answer)).value == 2
    assert len(fake.requests) == 3
