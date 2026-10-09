from backend.report.calibration import compare

KEY = [
    {"projeto_id": "PRJ01", "classificacao": "Não elegível", "estado_1": "NÃO DEMONSTRADA", "estado_2": "NÃO DEMONSTRADA",
     "estado_3": "NÃO CARACTERIZADA", "estado_4": "DOCUMENTADA COMO ACEITE", "estado_5": "DOCUMENTADA PARA A CONFIGURAÇÃO"},
    {"projeto_id": "PRJ02", "classificacao": "Elegível", "estado_1": "DEMONSTRADA NO RECORTE", "estado_2": "DEMONSTRADA NO RECORTE",
     "estado_3": "INVESTIGADA", "estado_4": "DOCUMENTADA", "estado_5": "DOCUMENTADA NO ESCOPO"},
]


def test_compare_counts_hits_and_builds_confusion_matrix():
    ours = [dict(KEY[0]), dict(KEY[1], classificacao="Com ressalvas", estado_5="DOCUMENTADA COM LIMITE")]
    report = compare(KEY, ours)
    assert report.class_hits == 1 and report.total == 2
    assert report.confusion["Elegível"]["Com ressalvas"] == 1
    assert report.state_hits["estado_5"] == 1
    assert report.missing == []


def test_projects_missing_in_our_output_are_reported():
    assert compare(KEY, [KEY[0]]).missing == ["PRJ02"]
