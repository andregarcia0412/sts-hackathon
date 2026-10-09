import pytest

from backend.catalog.loader import CatalogError, load_catalog, parse_catalog

ACTIVE_BY_CRITERION = {"NOV": 18, "CRI": 14, "INC": 15, "SIS": 10, "REP": 9}
ABSORBED = {"NOV-D7", "NOV-D9", "CRI-D9", "INC-D11", "INC-D13", "SIS-D6", "SIS-D8", "SIS-D9", "SIS-D11"}
NOT_APPLICABLE = {"NOV-D8", "SIS-D4", "SIS-D10", "REP-D5"}
PARTIAL = {"CRI-D3", "CRI-D7", "SIS-D3", "REP-D4"}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_has_66_active_criterion_rules(catalog):
    active = [r for r in catalog.rules if r.bloco != "transversal" and not r.absorvida_em]
    assert len(active) == 66
    for criterion, count in ACTIVE_BY_CRITERION.items():
        assert sum(r.criterio == criterion for r in active) == count, criterion
    assert sum(r.bloco == "web" for r in active) == 17


def test_absorbed_rules_are_markers_pointing_to_existing_rules(catalog):
    absorbed = {r.id: r for r in catalog.rules if r.absorvida_em}
    assert set(absorbed) == ABSORBED
    for rule in absorbed.values():
        assert all(catalog.get(target) for target in rule.absorvida_em)
        assert not rule.executavel


def test_transversal_rules_t1_to_t15(catalog):
    assert [r.id for r in catalog.rules if r.bloco == "transversal"] == [f"T{n}" for n in range(1, 16)]


def test_ids_are_unique(catalog):
    ids = [r.id for r in catalog.rules]
    assert len(ids) == len(set(ids))


def test_status_of_na_and_partial_rules_with_reason(catalog):
    assert {r.id for r in catalog.rules if r.status == "na" and r.bloco != "transversal"} == NOT_APPLICABLE
    assert {r.id for r in catalog.rules if r.status == "parcial"} == PARTIAL
    for rule in catalog.rules:
        if rule.status in ("na", "parcial"):
            assert rule.motivo_status


def test_every_executable_llm_rule_has_prompt_and_routing(catalog):
    for rule in catalog.executable_rules():
        assert rule.explicacao_simples, rule.id
        if rule.needs_llm:
            assert rule.prompt, rule.id
            assert rule.roteamento, rule.id


def test_informative_and_gate_roles(catalog):
    informative = {r.id for r in catalog.rules if r.papel == "informativa"}
    assert informative == {"NOV-W1", "NOV-W2", "NOV-W8"}
    assert {"NOV-W3", "NOV-D4", "NOV-D10", "CRI-D5"} <= {r.id for r in catalog.rules if r.papel == "gate"}


def test_doc_routing_uses_known_anchors(catalog):
    for rule in catalog.executable_rules():
        if rule.bloco == "doc":
            for anchor in rule.roteamento:
                assert anchor.split("#")[0] in catalog.file_types, (rule.id, anchor)


def test_criteria_vocabulary(catalog):
    assert catalog.criteria["REP"].estados.positivo == ["DOCUMENTADA NO ESCOPO", "DOCUMENTADA COM LIMITE"]
    assert catalog.criteria["INC"].estados.indeterminado == "ALEGADA, NÃO VERIFICÁVEL"
    assert catalog.criteria["SIS"].nome == "Sistematicidade"


def test_rules_for_criterion_split_by_block(catalog):
    web = catalog.rules_for("NOV", "web")
    assert [r.id for r in web] == [f"NOV-W{n}" for n in range(1, 9)]
    assert all(r.bloco == "doc" for r in catalog.rules_for("SIS", "doc"))
    assert catalog.rules_for("SIS", "web") == []


def test_duplicate_id_is_rejected():
    raw = {
        "versao": "x",
        "tipos_de_arquivo": ["metodo"],
        "criterios": {},
        "regras": [{"id": "T1", "bloco": "transversal", "titulo": "a"}, {"id": "T1", "bloco": "transversal", "titulo": "b"}],
    }
    with pytest.raises(CatalogError, match="duplicate"):
        parse_catalog(raw)
