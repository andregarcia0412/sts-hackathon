from types import SimpleNamespace

import pytest

from backend.llm.client import LLMError
from backend.llm.usage import current_usage, meter_scope
from tests.unit.test_llm_client import Answer, FakeOllama, make_client


class CountingOllama(FakeOllama):
    async def chat(self, **kwargs):
        response = await super().chat(**kwargs)
        return SimpleNamespace(message=response.message, prompt_eval_count=100, eval_count=20)


async def test_meter_records_calls_tokens_and_schema_retries_per_role():
    client, _ = make_client([])
    client._chat = CountingOllama(['{"value": "x"}', '{"value": 7}'])
    with meter_scope() as usage:
        await client.structured([{"role": "user", "content": "?"}], Answer, role="judge")
    judge = usage.roles["judge"]
    assert (judge.calls, judge.schema_retries, judge.prompt_tokens, judge.completion_tokens) == (2, 1, 200, 40)
    assert judge.llm_seconds >= 0
    assert usage.total().calls == 2


async def test_meter_records_transport_retries_and_failures():
    client, _ = make_client([ConnectionError("a"), '{"value": 1}', ConnectionError("b"), ConnectionError("c")])
    with meter_scope() as usage:
        await client.chat([{"role": "user", "content": "?"}], role="doc")
        with pytest.raises(LLMError):
            await client.chat([{"role": "user", "content": "?"}], role="doc")
    doc = usage.roles["doc"]
    assert (doc.calls, doc.transport_retries, doc.failures) == (1, 2, 1)


async def test_without_meter_nothing_is_recorded():
    client, _ = make_client(['{"value": 1}'])
    await client.structured([{"role": "user", "content": "?"}], Answer)
    assert current_usage() is None
