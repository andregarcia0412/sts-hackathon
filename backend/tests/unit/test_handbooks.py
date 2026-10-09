import re

from backend.catalog.handbooks import SECTIONS, handbook, pitfalls, section
from backend.catalog.loader import get_catalog
from backend.catalog.models import CRITERIA_ORDER
from backend.criteria.schemas import CriterionResult
from backend.graph.options import JudgeOptions
from backend.graph.states import StateJudgeOut, judge_state
from backend.llm.prompts import prompt_hashes
from tests.factories import evidence, run
from tests.fakes import FakeLLM


def test_every_criterion_has_a_handbook_with_the_three_sections():
    for criterion in CRITERIA_ORDER:
        text = handbook(criterion)
        for title in SECTIONS:
            assert section(criterion, title), f"{criterion}: missing section {title}"
        assert len(text.split()) < 1100, f"{criterion}: handbook too long for the judge prompt"


def test_handbooks_cite_only_catalog_rules_and_never_a_project_code():
    catalog = get_catalog()
    for criterion in CRITERIA_ORDER:
        text = handbook(criterion)
        assert not re.search(r"PRJ\d+", text)
        for rule_id in re.findall(r"\b(?:NOV|CRI|INC|SIS|REP)-[DW]\d+\b", text):
            assert catalog.get(rule_id), f"{criterion}: unknown rule {rule_id}"


def test_handbooks_are_registered_prompts():
    hashes = prompt_hashes()
    assert {f"graph.state.{c}" for c in CRITERIA_ORDER} <= set(hashes)


async def test_judge_prompt_carries_only_its_criterion_handbook():
    result = CriterionResult(criterion="INC", rules=[run("INC-D12", evidence("INC-D12", nature="derivado"))])
    llm = FakeLLM({StateJudgeOut: StateJudgeOut(estado="INVESTIGADA", justificativa="x")})
    await judge_state(llm, get_catalog(), result, True, options=JudgeOptions(handbooks=True))
    system = llm.calls_for(StateJudgeOut)[0][0]["content"]
    assert pitfalls("INC") in system and pitfalls("SIS") not in system
    llm = FakeLLM({StateJudgeOut: StateJudgeOut(estado="INVESTIGADA", justificativa="x")})
    await judge_state(llm, get_catalog(), result, True, options=JudgeOptions(handbooks=False))
    assert "<handbook" not in llm.calls_for(StateJudgeOut)[0][0]["content"]


async def test_doc_sub_gets_the_pitfalls_only_when_enabled():
    from backend.criteria.doc_sub import DocSubOut, run_doc_sub
    from tests.factories import fake_doc_sub, synthetic_canonical

    canonical = await synthetic_canonical()
    rules = get_catalog().rules_for("SIS", "doc")
    for enabled in (False, True):
        llm = FakeLLM({DocSubOut: fake_doc_sub})
        await run_doc_sub(llm, get_catalog(), "SIS", rules, canonical, 300, pitfalls=enabled)
        assert (pitfalls("SIS") in llm.calls_for(DocSubOut)[0][0]["content"]) is enabled
