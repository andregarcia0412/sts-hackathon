"""Regras NOV-W1..W8 (Bloco A, busca na internet) de `criterios/Novidade — Regras de Validação.md`."""

from ai_microservice.rules import Rule

CRITERIO = "novidade"

NOVELTY_WEB_RULES: list[Rule] = [
    Rule(
        id="NOV-W1",
        criterio=CRITERIO,
        titulo="Data de referência = início do projeto",
        o_que_verificar="Só é estado da arte o que estava acessível ao público antes da data de início do projeto.",
        evidencia_esperada="Data de início do projeto + data de publicação de cada resultado.",
        fontes_normativas=["LPI art. 11 §1º", "INPI Res. 169/2016 itens 3.1 e 3.3", "HMRC GfC3 parte 2, passo 5", "IE TDM §8.1(e)"],
        evaluator="procedural",
    ),
    Rule(
        id="NOV-W2",
        criterio=CRITERIO,
        titulo="Busca em três frentes",
        o_que_verificar="A busca cobriu patentes, literatura científica e soluções de mercado/concorrentes.",
        evidencia_esperada="Lista de bases consultadas por frente.",
        fontes_normativas=["IT MIMIT 2024 §1.1.3.1", "AU R&DTI"],
        evaluator="procedural",
    ),
    Rule(
        id="NOV-W3",
        criterio=CRITERIO,
        titulo="Elemento novo vs. documento mais próximo",
        o_que_verificar=(
            "Comparar o elemento novo declarado (o conhecimento/técnica, não o produto) com o documento mais próximo. "
            "Se um único documento já descreve o elemento inteiro, não há novidade."
        ),
        evidencia_esperada="Documento mais próximo + o que o projeto tem que o documento não tem.",
        fontes_normativas=["Frascati 2015 §2.16", "INPI itens 4.6 e 4.10", "EPO G-VII 5, etapa (i)"],
        como_julgar=(
            "enquadra = nenhum documento sozinho descreve o elemento novo inteiro; nao_enquadra = ao menos um documento (anterior à data de referência) já descreve o elemento inteiro."
        ),
        evaluator="llm",
    ),
    Rule(
        id="NOV-W4",
        criterio=CRITERIO,
        titulo="Novidade no setor, não só na empresa",
        o_que_verificar=(
            "Comparar com o setor/campo, não com a empresa: algo que já existe no mercado ou já é usado por outros "
            "atores do setor, mas é novo para a empresa, NÃO é novo."
        ),
        evidencia_esperada="Ausência de uso da solução por outros atores do setor.",
        fontes_normativas=["Frascati 2015 §2.15", "UK DSIT ¶6, ¶20, ¶22", "IE TDM §3.4", "IT MIMIT §1.1.3.1", "FAQ MCTI P4(a)"],
        como_julgar=(
            "enquadra = não há sinal de que a solução já era usada por outros atores do setor; nao_enquadra = fontes mostram a solução já em uso no setor (é novidade só para a empresa)."
        ),
        evaluator="llm",
    ),
    Rule(
        id="NOV-W5",
        criterio=CRITERIO,
        titulo="Resultado conhecido, método não público",
        o_que_verificar=(
            "Se outra empresa já chegou ao resultado mas o COMO não é público (segredo industrial), a novidade se mantém."
        ),
        evidencia_esperada="Ausência de documentação pública sobre o método.",
        fontes_normativas=["UK DSIT ¶11, ¶21", "IE TDM §3.4", "IT MIMIT §1.1.3.1"],
        como_julgar=(
            "enquadra = outros chegaram a resultado parecido, mas nenhuma fonte descreve publicamente o método; nao_enquadra = o método está descrito publicamente. Se nenhuma fonte chegou a resultado parecido, a regra não se aplica: use inconclusivo e diga isso."
        ),
        evaluator="llm",
    ),
    Rule(
        id="NOV-W6",
        criterio=CRITERIO,
        titulo="Trabalho simultâneo e independente",
        o_que_verificar=(
            "Trabalho simultâneo e independente de concorrentes não elimina a novidade se os resultados deles não "
            "estavam acessíveis antes do início do projeto."
        ),
        evidencia_esperada="Datas das publicações dos concorrentes vs. início do projeto.",
        fontes_normativas=["UK DSIT ¶21", "IE TDM §3.4", "IT MIMIT §1.1.3.1"],
        como_julgar=(
            "enquadra = trabalhos parecidos de terceiros só ficaram públicos depois da data de referência (simultâneos/independentes); nao_enquadra = já estavam públicos antes. Considere também as fontes posteriores à data de referência."
        ),
        evaluator="llm",
    ),
    Rule(
        id="NOV-W7",
        criterio=CRITERIO,
        titulo="Página web como estado da técnica",
        o_que_verificar=(
            "Página da internet conta como estado da técnica se pode ser achada por buscador público e tem data "
            "verificável anterior ao início do projeto."
        ),
        evidencia_esperada="URL + data de publicação ou de captura.",
        fontes_normativas=["INPI Res. 169/2016 item 3.33"],
        como_julgar=(
            "Considere só páginas web (frentes patentes e mercado). enquadra = nenhuma página com data verificável anterior à referência descreve o elemento novo; nao_enquadra = existe página assim. Páginas sem data verificável não contam como estado da técnica."
        ),
        evaluator="llm",
    ),
    Rule(
        id="NOV-W8",
        criterio=CRITERIO,
        titulo="Busca reproduzível",
        o_que_verificar="A busca está registrada: bases, data, string exata, filtros, nº de resultados, selecionados e por quê.",
        evidencia_esperada="Log de busca.",
        fontes_normativas=["PRISMA-S (Rethlefsen et al. 2021)", "WIPO Pub. 946"],
        evaluator="procedural",
    ),
]
