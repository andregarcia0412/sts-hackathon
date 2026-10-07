from ai_microservice.modules.novelty.evaluator import evaluate_rules, judge_rule
from ai_microservice.modules.novelty.rules import NOVELTY_WEB_RULES
from ai_microservice.modules.novelty.schemas import EvidenceCitation, FrontResult, RuleJudgement, SearchLogEntry
from ai_microservice.rules import RuleStatus
from tests.factories import make_doc, make_profile
from tests.fakes import FakeLLM

RULES = {rule.id: rule for rule in NOVELTY_WEB_RULES}


def log_entry(frente: str, erro: str | None = None) -> SearchLogEntry:
    return SearchLogEntry(frente=frente, base="b", query="q", executado_em="2026-10-07T00:00:00Z", erro=erro)


def fronts_ok() -> list[FrontResult]:
    return [
        FrontResult(frente="literatura", fontes=[make_doc("d1"), make_doc("d2", anterior=False)], log=[log_entry("literatura")]),
        FrontResult(frente="patentes", fontes=[make_doc("d3", anterior=None, frente="patentes")], log=[log_entry("patentes")]),
        FrontResult(frente="mercado", fontes=[], log=[log_entry("mercado")]),
    ]


def judge_citing(*ids: str, status=RuleStatus.NAO_ENQUADRA) -> FakeLLM:
    citations = [EvidenceCitation(fonte_id=i, justificativa="porque sim") for i in ids]
    return FakeLLM({RuleJudgement: lambda _: RuleJudgement(status=status, resumo="r", evidencias=citations)})


async def test_all_eight_rules_are_answered_and_procedural_ones_skip_the_llm():
    llm = judge_citing("d1")
    verdicts = await evaluate_rules(llm, NOVELTY_WEB_RULES, make_profile(), fronts_ok())

    assert [v.id for v in verdicts] == [f"NOV-W{i}" for i in range(1, 9)]
    assert len(llm.calls) == 5  # W3..W7
    by_id = {v.id: v for v in verdicts}
    assert by_id["NOV-W1"].status == RuleStatus.ENQUADRA and "2025-01-06" in by_id["NOV-W1"].resumo
    assert "1 fonte(s) posterior(es)" in by_id["NOV-W1"].resumo
    assert by_id["NOV-W2"].status == RuleStatus.ENQUADRA
    assert by_id["NOV-W8"].status == RuleStatus.ENQUADRA


async def test_missing_front_fails_three_fronts_rule():
    fronts = fronts_ok()
    fronts[1] = FrontResult(frente="patentes", fontes=[], log=[log_entry("patentes", erro="frente interrompida")])
    verdicts = await evaluate_rules(judge_citing("d1"), [RULES["NOV-W2"]], make_profile(), fronts)
    assert verdicts[0].status == RuleStatus.NAO_ENQUADRA
    assert "patentes" in verdicts[0].resumo


async def test_hallucinated_source_is_dropped_and_verdict_downgraded():
    docs = [make_doc("d1")]
    verdict = await judge_rule(judge_citing("inventada"), RULES["NOV-W3"], make_profile(), docs)
    assert verdict.evidencias == []
    assert verdict.status == RuleStatus.INCONCLUSIVO


async def test_valid_citation_is_enriched_with_source_metadata():
    verdict = await judge_rule(judge_citing("d1", "inventada"), RULES["NOV-W3"], make_profile(), [make_doc("d1")])
    assert verdict.status == RuleStatus.NAO_ENQUADRA
    [evidence] = verdict.evidencias
    assert evidence.url == "https://example.org/d1" and evidence.data_publicacao == "2020-01-01"


async def test_later_sources_only_reach_rule_w6():
    docs = [make_doc("later", anterior=False)]
    w3 = await judge_rule(judge_citing("later"), RULES["NOV-W3"], make_profile(), docs)
    w6 = await judge_rule(judge_citing("later", status=RuleStatus.ENQUADRA), RULES["NOV-W6"], make_profile(), docs)
    assert w3.status == RuleStatus.INCONCLUSIVO and w3.evidencias == []
    assert w6.status == RuleStatus.ENQUADRA and w6.evidencias[0].fonte_id == "later"


async def test_interview_is_never_offered_as_a_source():
    llm = judge_citing("d1")
    await judge_rule(llm, RULES["NOV-W4"], make_profile(), [make_doc("d1")])
    prompt = llm.calls[0][1][-1]["content"]
    assert "entrevista" not in prompt.lower()
