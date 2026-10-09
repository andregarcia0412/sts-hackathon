from backend.assistant.norms import BM25Index, NormChunk, chunk_pages, norm_title

LEI_PAGE = """LEI No 11.196
Art. 17. A pessoa jurídica poderá usufruir de incentivos fiscais à inovação tecnológica.
§ 1o Considera-se inovação tecnológica a concepção de novo produto ou processo.
Art. 18. Poderão ser deduzidas as importâncias transferidas a microempresas."""

FRASCATI_PAGE = """2.14 Novelty is the key element of an R&D project in the business enterprise sector.
2.15 Results must be novel to the business and not already in use in the industry.
2.17 Creativity: the project must have novel concepts or hypotheses."""


def test_title_from_file_name():
    assert norm_title("Lei 11.196-2005 (Lei do Bem) - Planalto.pdf") == "Lei 11.196-2005 (Lei do Bem)"


def test_chunks_split_by_article_paragraph_and_numbered_section():
    chunks = chunk_pages("Lei 11.196", [LEI_PAGE])
    labels = [c.label for c in chunks]
    assert labels == ["p. 1", "Art. 17", "§ 1o", "Art. 18"]  # text before the first article is kept as page text
    assert chunks[1].page == 1
    assert "incentivos fiscais" in chunks[1].text
    assert [c.label for c in chunk_pages("Frascati 2015", [FRASCATI_PAGE])] == ["§2.14", "§2.15", "§2.17"]


def test_page_without_markers_becomes_one_chunk():
    [chunk] = chunk_pages("FAQ", ["Pergunta sem artigo nem parágrafo numerado."])
    assert chunk.label == "p. 1"


def test_bm25_ranks_relevant_chunk_first_accent_insensitive():
    chunks = chunk_pages("Lei", [LEI_PAGE]) + chunk_pages("Frascati", [FRASCATI_PAGE])
    index = BM25Index(chunks)
    top = index.search("o que é inovacao tecnologica?", k=2)
    assert top[0].label == "§ 1o"
    assert index.search("already in use in the industry", k=1)[0].label == "§2.15"
    assert BM25Index([]).search("x") == []


def test_norm_title_is_searchable():
    chunks = chunk_pages("Manual de Frascati 2015", [FRASCATI_PAGE]) + chunk_pages("Lei 11.196", [LEI_PAGE])
    index = BM25Index(chunks, key=lambda c: c.search_text)
    assert index.search("manual de frascati", k=1)[0].norm == "Manual de Frascati 2015"


def test_chunk_ids_are_stable():
    first = chunk_pages("Lei", [LEI_PAGE])
    assert [c.id for c in first] == [c.id for c in chunk_pages("Lei", [LEI_PAGE])]
    assert isinstance(first[0], NormChunk)
