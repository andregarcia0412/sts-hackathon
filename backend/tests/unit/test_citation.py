from backend.criteria.citation import quote_in


def test_exact_substring():
    assert quote_in("dois lotes dependem", "Ambos falham quando dois lotes dependem do mesmo saldo.")


def test_whitespace_and_line_breaks_are_normalised():
    assert quote_in("falham  quando\ndois", "Ambos falham quando dois lotes")


def test_wrapping_quotes_and_ellipsis_are_ignored():
    assert quote_in('"…falham quando dois..."', "Ambos falham quando dois lotes")


def test_paraphrase_and_empty_are_rejected():
    assert not quote_in("falham sempre que dois", "Ambos falham quando dois lotes")
    assert not quote_in("", "texto")
    assert not quote_in("...", "texto")


def test_case_is_part_of_the_verbatim_check():
    assert not quote_in("AMBOS FALHAM", "Ambos falham")
