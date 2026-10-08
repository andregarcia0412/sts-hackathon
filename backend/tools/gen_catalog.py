"""Gera catalog/rules.yaml a partir das notas de critério.

O catálogo é dado versionado; este script é a fonte da verdade e fica em tools/.
Roda: cd backend && .venv/bin/python tools/gen_catalog.py
"""
from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "catalog" / "rules.yaml"

# ---------------------------------------------------------------------------
# Artefatos do pacote (schema dos 14 arquivos uniformes)
# ---------------------------------------------------------------------------
ARTIFACTS = {
    "dossie_projeto.pdf": "sintese",
    "registro_tecnico.pdf": "sintese",
    "transcricao_entrevista_tecnica.pdf": "depoimento",
    "atividades.csv": "registro_primario",
    "atividades.xlsx": "registro_primario",
    "inventario_evidencias.csv": "indice",
    "evidencias/metodo.md": "sintese",
    "evidencias/cronologia.csv": "registro_primario",
    "evidencias/medicoes.csv": "registro_primario",
    "evidencias/resultados.csv": "derivado",
    "evidencias/configuracao.json": "especificacao",
    "evidencias/observacoes.csv": "registro_primario",
    "evidencias/entradas.csv": "registro_primario",
    "evidencias/revisao_tecnica.md": "revisao",
}

# ---------------------------------------------------------------------------
# Regras — conteúdo condensado das notas em docs/regras-criterios/
# ---------------------------------------------------------------------------
def R(
    id: str,
    criterion: str,
    block: str,
    mode: str,
    what: str,
    evidence: str,
    sources: list,
    routing: list,
    polarity: str,
    scoring: str,
    status: str = "aplicavel",
    status_reason: str | None = None,
    absorbed_into: str | None = None,
    chk: str | None = None,
    prompt: str | None = None,
    query_family: str | None = None,
):
    return {
        "id": id,
        "criterion": criterion,
        "block": block,
        "mode": mode,
        "what": what,
        "evidence": evidence,
        "sources": sources,
        "routing": routing,
    } | (
        {"chk": chk} if chk else {}
    ) | {
        "polarity_hint": polarity,
        "scoring_role": scoring,
        "status": status,
        "status_reason": status_reason,
        "absorbed_into": absorbed_into,
    } | (
        {"prompt": prompt} if prompt else {}
    ) | (
        {"query_family": query_family} if query_family else {}
    )


RULES: list[dict] = [
    # ================= NOVIDADE — 18 ativas =================
    R("NOV-W1", "novidade", "web", "regra", "Fixar a data de referência = início do projeto; só é estado da arte o que estava acessível ao público antes dela", "data de início (FORMP&D 3.1.11) + data de publicação de cada resultado", ["LPI art. 11 §1º", "INPI Res. 169/2016 itens 3.1 e 3.3", "HMRC GfC3 parte 2 passo 5", "IE TDM §8.1(e)"], ["evidencias/cronologia.csv"], "informativa", "informativa", chk="CHK-TEMPO"),
    R("NOV-W2", "novidade", "web", "web", "Buscar em três frentes: patentes, literatura científica e soluções de mercado/concorrentes", "lista de bases consultadas por frente", ["IT MIMIT 2024 §1.1.3.1", "AU R&DTI"], [], "informativa", "informativa", prompt="""Para o elemento novo declarado no metodo.md#2, monte e execute um plano de busca em três frentes:
(1) patentes — query com termos do mecanismo e classe IPC/CPC se aplicável (G06F, H04L, G06Q 40);
(2) literatura científica — query em PT e EN com sinônimos técnicos;
(3) mercado — query sobre a solução/setor.
Registra, para cada frente, a base, a string usada e quantos resultados voltaram (NOV-W8).
Achados posteriores à data de referência do projeto não são estado da arte.""", query_family="plano de busca"),
    R("NOV-W3", "novidade", "web", "web", "Comparar o elemento novo declarado (o conhecimento/técnica, não o produto) com o documento mais próximo; um único documento que descreva o elemento inteiro derruba a novidade", "documento mais próximo + quadro 'o que o projeto tem que o achado não tem'", ["Frascati §2.16", "INPI itens 4.6 e 4.10", "EPO G-VII 5 etapa (i)"], [], "negative", "mean", prompt="""A partir do elemento novo declarado no metodo.md#2, busque o documento público mais próximo dele.
Se um único resultado já descrever o elemento inteiro (o mecanismo, não só o resultado), a novidade
não está demonstrada — registra a evidência contrária com o trecho do achado (quote da fonte web).
Se nada cobrir o elemento, registra o achado mais próximo e o que falta nele.
IMPORTANTE: achar a técnica GENÉRICA na web não derruba a novidade se o mecanismo específico do
recorte não estiver descrito no achado.""", query_family="documento mais próximo"),
    R("NOV-W4", "novidade", "web", "web", "Comparar com o setor/campo, não com a empresa: algo que já existe no mercado mas é novo para a empresa NÃO é novo", "ausência de uso da solução por outros atores do setor", ["Frascati §2.15", "UK DSIT ¶6 ¶20 ¶22", "IE TDM §3.4", "FAQ MCTI P4(a)"], [], "negative", "mean", prompt="""Busque indícios de que a solução já era usada por outros atores do setor (bancos/fintechs para
projetos financeiros). Achado de uso setorial = evidência contrária; ausência de achado é registrada
com peso menor — nunca como prova de novidade.""", query_family="uso setorial"),
    R("NOV-W5", "novidade", "web", "web", "Se outra empresa já chegou ao resultado mas o COMO não é público (segredo industrial), a novidade se mantém", "ausência de documentação pública sobre o método", ["UK DSIT ¶11 ¶21", "IE TDM §3.4", "IT MIMIT §1.1.3.1"], [], "positive", "mean", prompt="""Busque se o resultado (a função) já aparece publicamente e verifique se o MÉTODO está público.
Resultado público + método secreto = novidade se mantém. Registra o achado e se ele descreve
o como ou só o resultado.""", query_family="resultado público vs método"),
    R("NOV-W6", "novidade", "web", "web", "Trabalho simultâneo e independente de concorrentes não elimina a novidade, se os resultados deles não estavam acessíveis", "datas das publicações dos concorrentes vs. início do projeto", ["UK DSIT ¶21", "IE TDM §3.4", "IT MIMIT §1.1.3.1"], [], "positive", "mean", prompt="""Compare a data de publicação dos achados com a data de referência do projeto (primeiro evento
da cronologia). Achado posterior é trabalho simultâneo — não derruba a novidade; registra a data.
Achado anterior é estado da técnica.""", query_family="datas de publicação"),
    R("NOV-W7", "novidade", "web", "web", "Página da internet conta como estado da técnica se pode ser achada por buscador público e continuou acessível", "URL + data de publicação ou de captura", ["INPI Res. 169/2016 item 3.33"], [], "informativa", "informativa", prompt="""Para cada achado usado, registra a URL e a data de captura (dia de hoje) — define a admissibilidade
da evidência web no grafo. Achado sem data confiável = 'data indeterminada' (não conta como anterior
nem posterior).""", query_family="admissibilidade"),
    R("NOV-W8", "novidade", "web", "web+regra", "Registrar a busca de forma reproduzível: bases, data, string exata, filtros, nº de resultados, selecionados e por quê", "log de busca (vira nó do grafo)", ["PRISMA-S (Rethlefsen et al. 2021)", "WIPO Pub. 946"], [], "informativa", "informativa", prompt="""Não gera evidência própria: o log de busca é gerado automaticamente pelo sistema para toda query
que você executar. Confere apenas que você registrou, para cada regra web que rodou, quantas queries
fez e quantos achados selecionou.""", query_family="log de busca"),
    R("NOV-D1", "novidade", "documento", "llm", "O projeto declara explicitamente o elemento novo: a tecnologia, as novas funcionalidades/características e a aplicação", "texto do campo 3.1.7 ou do relatório técnico", ["FORMP&D 3.1.7", "Guia MCTI 2020 §6.2", "FAQ MCTI P4(a) e (c)"], ["evidencias/metodo.md#2"], "positive", "mean", prompt="""No §2 'Mecanismo e hipótese' do metodo.md, identifique a declaração de elemento novo do projeto.
O que a equipe afirma ser novo? Cite literalmente o trecho que descreve o mecanismo/hipótese. Se o
documento não declara elemento novo (só adequação de configuração), registre evidência contrária."""),
    R("NOV-D2", "novidade", "documento", "llm", "O projeto descreve o estado da arte no início: alternativas conhecidas e o modo de falha específico de cada uma; só lista de ferramentas → novidade indeterminada", "seção de estado da arte (metodo.md#1) com alternativa + limitação, datada", ["Guia MCTI 2020 §6.2", "IT MIMIT §1.1.3.1", "IE TDM §8.1(e)", "Históricos PRJ02/03/05/06/13-16/18 × PRJ08"], ["evidencias/metodo.md#1"], "positive", "mean", prompt="""No §1 'Referência anterior' do metodo.md, verifique se o projeto descreve alternativas conhecidas
E onde cada uma falha no problema estudado. Alternativa + limitação = sustenta. Lista de ferramentas
sem modo de falha → registra neutra com a limitação. Sem referência anterior → sem evidência."""),
    R("NOV-D3", "novidade", "documento", "llm", "A novidade é de conhecimento/técnica (o 'como'), não de funcionalidade, negócio ou mercado", "trechos que explicam o problema técnico e a abordagem", ["FAQ MCTI P4", "Frascati §2.16 e Tab. 2.1(a)", "Guia MCTI 2020 §6.1"], ["evidencias/metodo.md#2"], "positive", "mean", prompt="""Analise se o elemento novo declarado é conhecimento/técnica (como fazer) ou apenas funcionalidade/
negócio. Cite o trecho que mostra o mecanismo técnico. Funcionalidade sem mecanismo → contrária."""),
    R("NOV-D4", "novidade", "documento", "llm", "Não é cópia, imitação, engenharia reversa, compra de tecnologia nem nacionalização/adaptação sem barreira técnica", "origem da solução; contratos de licença ou aquisição", ["Frascati §2.15", "UK DSIT ¶12 ¶22 ¶24", "Guia ANPEI 2017 pp. 19 e 26", "Guia MCTI 2020 Ap. B.3"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "negative", "gate", chk="CHK-CONFIG", prompt="""Use o resultado da checagem CHK-CONFIG (via tool chk_resultado). Se a referência anterior do §1 é
manual/catálogo/produto contratado que já fornece a função aplicada no §2, a solução é adaptação de
tecnologia existente → contrária. Cite o trecho do §1/§2 que mostra a origem da solução."""),
    R("NOV-D5", "novidade", "documento", "llm", "Software: não cai nas exclusões (sistema de negócio com métodos conhecidos, funcionalidade de usuário, ferramentas prontas, customização, depuração rotineira)", "técnica/arquitetura descrita vs. lista de exclusões", ["Frascati §2.70–2.72", "IPCTN 2020 Anexo I"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "negative", "mean", prompt="""Compare o mecanismo do §2 contra as exclusões de software: sistema de negócio com métodos conhecidos,
funcionalidade de usuário, site com ferramentas prontas, customização, depuração rotineira. Cite o
trecho do §2 que caracteriza o mecanismo. Se o mecanismo é configuração/uso de ferramenta pronta →
contrária; se descreve técnica própria → sustenta."""),
    R("NOV-D6", "novidade", "documento", "regra", "A melhoria é substancial e objetiva: há comparação com a linha de base; melhora numérica entre versões SOZINHA não basta (rotina também melhora)", "métricas antes/depois, benchmark", ["Decreto 5.798 art. 2º II 'c'", "Guia MCTI 2020 Ap. B.1", "UK DSIT ¶23–25", "IT MIMIT §1.1.3.1", "Histórico PRJ01 8/12→12/12 só mudando retenção"], ["evidencias/medicoes.csv", "evidencias/resultados.csv"], "positive", "mean", chk="CHK-RECALC", prompt="""Use o resultado da CHK-RECALC (via tool chk_resultado) sobre a comparação entre versões. A regra:
melhora numérica entre versões sozinha não demonstra novidade — rotina também melhora. Só registra
evidência sustentando se houver comparação qualitativa além da melhora numérica."""),
    R("NOV-D8", "novidade", "documento", "regra", "Patente, registro de software, artigo ou aprovação por agência de fomento são indícios — não obrigatórios", "nº do pedido/registro, DOI, termo de outorga", ["IT MIMIT §1.1.3.1", "Frascati Tab. 2.1(d)", "Guia ANPEI 2017 Fig. 1"], [], "positive", "informativa", status="na", status_reason="N/A no pacote — não há patentes, registros ou artigos nos artefatos"),
    R("NOV-D10", "novidade", "documento", "regra+llm", "Se a referência anterior — manual, catálogo, dicionário ou produto contratado, datado antes do projeto — já fornece a função aplicada, a novidade não está demonstrada", "referência anterior + data (cronologia) + mecanismo do §2", ["Históricos PRJ01 (BARR-2), PRJ04, 09, 11, 12, 19, 20", "Frascati §2.72"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "negative", "gate", chk="CHK-CONFIG", prompt="""Combine o resultado da CHK-CONFIG com as datas da CHK-TEMPO (tools chk_resultado). Passo a passo:
(1) a referência do §1 é manual/catálogo/produto contratado? (2) ela é datada antes do início do
projeto? (3) o §2 aplica a função que ela já fornece? Se sim nos três → novidade NÃO demonstrada,
evidência contrária citando o trecho do §1 e do §2. Se algum passo falha → neutra explicando."""),
    R("NOV-D11", "novidade", "documento", "llm", "A novidade vale no recorte ensaiado (perfis, cenários, cargas); afirmações gerais além dele não são cobertas", "seção 'Limite da conclusão' (metodo.md#6)", ["Históricos PRJ02, 05, 07, 14", "LEIA_ME"], ["evidencias/metodo.md#6"], "positive", "mean", chk="CHK-ESCOPO", prompt="""No §6 'Limite da conclusão', identifique o recorte da novidade. Cite o trecho que delimita onde a
conclusão vale. A regra apenas delimita — não é positiva nem negativa por si; registre a polaridade
neutra com a citação do limite."""),
    R("NOV-D12", "novidade", "documento", "llm", "Título ou adjetivo comercial não prova novidade — decide o mecanismo documentado; técnica genérica só conta com elemento técnico próprio testado contra o comparador", "mecanismo do §2 vs. título do dossiê", ["Históricos PRJ09, PRJ19, PRJ02", "T13"], ["dossie_projeto.pdf", "evidencias/metodo.md#2"], "positive", "mean", chk="CHK-VERSOES", prompt="""Compare o título do dossiê (fragmento 1) com o mecanismo do §2. O título/adjetivo não prova nada;
o mecanismo é o que decide. Se o §2 descreve técnica genérica sem elemento próprio testado contra
o comparador → contrária. Se há elemento próprio além do título → sustenta citando o mecanismo."""),

    # ================= CRIATIVIDADE — 14 ativas =================
    R("CRI-W1", "criatividade", "web", "web+llm", "Aplicar o roteiro problema-solução EPO: achar o estado da arte mais próximo, definir o problema técnico, verificar se um técnico chegaria à solução de forma óbvia", "documento mais próximo + problema técnico + justificativa da não-obviedade", ["EPO G-VII 5", "INPI Res. 169/2016 itens 5.9–5.21", "LPI art. 13", "Guia MCTI 2020 §6"], [], "negative", "mean", prompt="""Reaproveite o achado mais próximo da NOV-W3 (se disponível no contexto) e derive o problema técnico
objetivo. Depois: um técnico no assunto chegaria à solução do projeto de forma óbvia? A justificativa
de não-obviedade é sinal, não veredito. Cite o trecho do achado e a justificativa.""", query_family="problema-solução EPO"),
    R("CRI-W2", "criatividade", "web", "web+llm", "Se a abordagem do projeto aparece como prática padrão (documentação oficial, tutorial, manual), é rotina", "link do material que descreve a mesma abordagem", ["Guia do desafio Parte 4", "Frascati §2.72"], [], "negative", "gate", chk="CHK-CONFIG", prompt="""A configuração do §2 aparece em documentação oficial ou tutorial? Busque (1–2 queries) a prática
descrita no mecanismo. Achado que descreve a mesma abordagem como prática padrão → contrária (gate).
Use também o resultado da CHK-CONFIG (tool chk_resultado).""", query_family="prática padrão/tutorial"),
    R("CRI-W3", "criatividade", "web", "llm+regra", "Combinação de elementos conhecidos só é criativa se o efeito conjunto vai além da soma dos efeitos isolados; justaposição simples é óbvia", "comparação dos efeitos isolados vs. combinados", ["INPI itens 5.22 e 5.30"], ["evidencias/medicoes.csv"], "negative", "mean", prompt="""O §2 vs. comparadores isolados — as estratégias alternativas medidas estão no medicoes.csv? (tool
buscar_em_arquivos). Combinação com efeito além da soma → sustenta; justaposição → contrária."""),
    R("CRI-W4", "criatividade", "web", "llm", "Trazer conhecimento de outro campo conta quando a adaptação não era facilmente dedutível", "origem do conhecimento + o que precisou ser adaptado", ["UK DSIT ¶6 e ¶23", "IT MIMIT 2024 §1.1.3.2", "Frascati Tab. 2.1(b)"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "positive", "mean", prompt="""Procure no §1/§2 indícios de conhecimento importado de outro campo e o que precisou ser adaptado.
Cite o trecho. Sem indício → sem evidência (não contrária)."""),
    R("CRI-W5", "criatividade", "web", "web", "Indícios a favor: o problema era conhecido há tempo e não resolvido, ou o projeto seguiu caminho contrário ao consenso técnico", "literatura relatando o problema em aberto ou o consenso contrariado", ["INPI itens 5.57 e 5.58"], [], "positive", "mean", prompt="""Busque (1–2 queries) literatura ou relatórios mostrando o problema técnico SEM solução conhecida ou
um consenso técnico contrariado. Achado → sustenta com o trecho. Nada → sem evidência.""", query_family="problema em aberto"),
    R("CRI-D1", "criatividade", "documento", "regra+llm", "Há hipótese explícita (ideia ou abordagem para superar a barreira), registrada antes dos testes", "plano, ata ou relatório datado com a hipótese", ["Guia MCTI 2020 §6.2", "CRA SR&ED", "AU R&DTI", "IE TDM §8.1(f)"], ["evidencias/metodo.md#2"], "positive", "mean", chk="CHK-TEMPO", prompt="""Duas partes: (1) REGRA — use a CHK-TEMPO (tool chk_resultado): o evento 'Registro do problema e das
referências' (documento-inicial) é anterior aos ensaios? (2) LLM — no §2, identifique a hipótese
explícita e cite-a. Hipótese + registro anterior → sustenta; hipótese sem data anterior → neutra;
sem hipótese → contrária."""),
    R("CRI-D2", "criatividade", "documento", "llm", "Há obstáculo técnico que exigiu solução original, descrito de forma concreta", "campo 3.1.8 (barreira) / relatório técnico", ["IT MIMIT §1.1.3.2", "Guia MCTI 2020 §6.3", "FORMP&D 3.1.8"], ["dossie_projeto.pdf", "atividades.csv"], "positive", "mean", prompt="""Na pergunta registrada do dossiê e na fase 'Caracterização do problema' do atividades.csv, identifique
o obstáculo técnico concreto. Cite o trecho. Barreira descrita em termos de mercado/cliente →
contrária; sem menção → sem evidência."""),
    R("CRI-D3", "criatividade", "documento", "regra", "A equipe inclui pesquisador — e dá para saber quem formulou a hipótese, com qual qualificação e dedicação", "lista da equipe com titulação, função e horas", ["Frascati §2.17 §2.19 §5.35–5.36 Tab. 2.1(e)", "Decreto 5.798 art. 2º III"], ["atividades.csv"], "positive", "mean", status="parcial", status_reason="parcial: atividades.csv só traz responsavel_por_funcao (função, sem titulação) — limitação registrada"),
    R("CRI-D4", "criatividade", "documento", "llm+regra", "Estão registradas as alternativas consideradas e as abandonadas, inclusive os insucessos", "registro de decisões técnicas, experimentos descartados", ["IT MIMIT §1.1.3.2", "IE TDM §3.1", "26 CFR §1.41-4(a)(5)", "Históricos"], ["evidencias/observacoes.csv"], "positive", "mean", chk="CHK-VERSOES", prompt="""Combine: CHK-VERSOES (comparadores rodados) + CHK-FALHAS (versões abandonadas) via chk_resultado,
e o observacoes.csv (tool buscar_em_arquivos). Alternativas registradas → sustenta citando o trecho;
só a versão final → sem evidência."""),
    R("CRI-D5", "criatividade", "documento", "llm+regra", "A mudança não é rotineira: não se resume a configurar/ativar/cadastrar/mapear campos/ajustar parâmetro dentro da faixa já suportada, sem alterar o algoritmo", "o que mudou tecnicamente; verbos do mecanismo; frases como 'nenhum algoritmo foi modificado'", ["Frascati §2.17 e §2.56", "Guia MCTI 2020 Ap. B.1", "FAQ MCTI P17", "Históricos PRJ01, 04, 09, 11, 12, 19, 20"], ["evidencias/metodo.md#2", "evidencias/configuracao.json"], "negative", "gate", chk="CHK-CONFIG", prompt="""Use CHK-CONFIG (tool chk_resultado): o mecanismo é configurar/ativar/mapear/ajustar dentro da faixa
suportada? Procure no §2 frases como 'nenhum algoritmo foi modificado' e verbos de configuração.
Mudança dentro da faixa → contrária (gate). Alteração de algoritmo/mecanismo próprio → sustenta."""),
    R("CRI-D6", "criatividade", "documento", "llm", "Método novo para tarefa comum CONTA (ex.: novo método de processamento de dados)", "descrição do método e do que ele tem de diferente", ["Frascati §2.17", "IT MIMIT §1.1.3.2"], ["evidencias/metodo.md#2"], "positive", "mean", prompt="""Verifique se o §2 descreve um método novo para uma tarefa comum. Se sim → sustenta (polaridade
POSITIVA — evita viés de rejeição). Cite o trecho do método. Sem método novo → sem evidência."""),
    R("CRI-D7", "criatividade", "documento", "llm", "Quem afirma a criatividade/avanço é profissional competente na área, não alguém só com interesse no tema", "currículo / justificativa assinada", ["HMRC GfC3 parte 3"], ["evidencias/revisao_tecnica.md"], "positive", "mean", status="parcial", status_reason="parcial: mesma limitação da CRI-D3; revisao_tecnica.md dá só a função 'revisão técnica', sem titulação"),
    R("CRI-D8", "criatividade", "documento", "regra+llm", "O mecanismo está especificado com regra de decisão e parâmetros concretos (limiares, pesos, janelas, empate), não só nome de técnica; null → indeterminada", "metodo.md#2, #4 e configuracao.json (parâmetros não nulos)", ["Históricos PRJ02, 03, 13 × PRJ08, 10, 17"], ["evidencias/metodo.md#2", "evidencias/metodo.md#4", "evidencias/configuracao.json"], "positive", "mean", chk="CHK-VERSOES", prompt="""Duas partes: (1) REGRA — CHK-VERSOES (tool chk_resultado): parâmetros-chave não nulos no
configuracao.json? (2) LLM — o §2/§4 traz regra de decisão com limiares/empate concretos? Parâmetros
concretos + regra → sustenta; null/só nome de técnica → neutra (indeterminada)."""),
    R("CRI-D10", "criatividade", "documento", "llm+regra", "A criatividade não exige inventar primitiva: pode estar em acoplamento/combinação original testada contra os conhecidos; renomear técnica conhecida não conta", "mecanismo vs. comparadores nomeados no §1", ["Históricos PRJ05, PRJ07, PRJ03", "Frascati Tab. 2.1(b)"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "positive", "mean", chk="CHK-VERSOES", prompt="""Use CHK-VERSOES (comparadores rodados) + o §1. A combinação foi testada contra os conhecidos?
Combinação original testada → sustenta; renomear técnica conhecida → contrária."""),

    # ================= INCERTEZA — 15 ativas =================
    R("INC-W1", "incerteza", "web", "web", "A solução da barreira já estava disponível ou era facilmente dedutível por profissional competente na data de início?", "resultados de busca sobre a barreira (com data)", ["UK DSIT ¶13–14", "CRA SR&ED", "AU R&DTI", "IE TDM §3.4", "HMRC GfC3 parte 2 passo 4"], [], "negative", "mean", prompt="""Busque a SOLUÇÃO DA BARREIRA declarada (não o produto). Query sobre como resolver o problema técnico.
Achado anterior à data de referência que resolve a barreira → contrária. Nada → registra ausência
com peso menor.""", query_family="solução da barreira"),
    R("INC-W2", "incerteza", "web", "web", "Não saber internamente não é incerteza: se a solução era razoavelmente acessível (publicada, consultoria, especialista), a falta de know-how não conta", "evidência de que a solução não estava publicada nem disponível", ["IE TDM §3.4", "IT MIMIT 2024 §1.1.3.3", "CRA SR&ED"], [], "negative", "mean", prompt="""Busque (1–2 queries) se a solução da barreira estava acessível (artigo, consultoria, especialista).
Acessível → contrária. Nada → ausência com peso menor.""", query_family="acessibilidade da solução"),
    R("INC-W3", "incerteza", "web", "web", "A literatura ou documentação técnica relata o problema como em aberto ou aponta limitações das soluções existentes", "trechos de artigos/issues/relatórios que descrevem a limitação", ["Guia MCTI 2020 §6.2", "INPI item 5.57"], [], "positive", "mean", prompt="""Busque (1–2 queries) artigos/issues/relatórios descrevendo a limitação técnica que o projeto ataca
como problema em aberto. Achado → sustenta citando o trecho.""", query_family="problema relatado em aberto"),
    R("INC-W4", "incerteza", "web", "web", "Maturidade da tecnologia no setor como indício: quanto mais baixo o TRL, maior a incerteza (heurística)", "TRL estimado com base no que foi encontrado", ["Guia MCTI 2020 §6.2", "ISO 16290:2013", "NASA TRL"], [], "positive", "informativa", prompt="""Com base nos achados web, estime o TRL da técnica (artigo ≈ 2–4; biblioteca madura ≈ 7–8; produto
comercial = 9) com justificativa. Registra como indício (informativa), não prova.""", query_family="TRL"),
    R("INC-D1", "incerteza", "documento", "llm", "A incerteza é técnica/científica e intrínseca — não de mercado, financiamento, prazo comercial nem regra de negócio ou política", "descrição do risco e da sua causa; origem das divergências", ["FAQ MCTI P4(b)", "IT MIMIT §1.1.3.3", "IE TDM §3.5", "Jalonen 2011", "Histórico PRJ20"], ["evidencias/metodo.md#2", "evidencias/revisao_tecnica.md", "evidencias/observacoes.csv"], "positive", "mean", prompt="""Analise se a incerteza declarada (§2, revisão técnica, observações) é técnica/científica. Risco
descrito como mercado/prazo/orçamento/política → contrária. Incerteza técnica → sustenta citando
o trecho. A transcrição da entrevista é DEPOIMENTO — use só como contexto, nunca como evidência."""),
    R("INC-D2", "incerteza", "documento", "regra+llm", "A incerteza está formulada como pergunta técnica específica", "lista nominal das incertezas", ["IE TDM §3.5(a)-(b)", "UK DSIT ¶13", "HMRC GfC3 parte 2 passo 3", "Guia MCTI 2020 §6.3"], ["atividades.csv", "dossie_projeto.pdf", "evidencias/metodo.md#2"], "positive", "mean", prompt="""Duas partes: (1) REGRA — há padrão 'Pergunta:' na coluna resultado_ou_saida do atividades.csv?
(tool buscar_em_arquivos). (2) LLM — a pergunta é técnica (não de negócio)? Pergunta técnica
registrada → sustenta citando-a; pergunta de negócio → contrária; sem pergunta → sem evidência."""),
    R("INC-D3", "incerteza", "documento", "llm", "O projeto explica por que um profissional competente não resolveria aquilo com o conhecimento disponível", "justificativa técnica", ["HMRC GfC3 parte 2 passo 4", "UK DSIT ¶14"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2"], "positive", "mean", prompt="""No §1/§2, o projeto explica por que o conhecimento disponível não resolvia? Justificativa presente →
sustenta citando-a. Ausente → sem evidência (não contrária)."""),
    R("INC-D4", "incerteza", "documento", "regra+llm", "Há sinais de que o resultado não era previsível: atrasos, falhas, reprojetos — desde que falhas EXPERIMENTAIS, não operacionais (INC-D9)", "relatórios de teste, registro de falhas", ["IT MIMIT §1.1.3.3", "Guia MCTI 2020 §6.3", "IE TDM §3.1", "T4"], ["evidencias/resultados.csv", "evidencias/observacoes.csv"], "positive", "mean", chk="CHK-FALHAS", prompt="""Use CHK-FALHAS (tool chk_resultado): só falha EXPERIMENTAL conta; 'v1 falhou → v2 corrigiu'
sozinho NÃO prova incerteza (os 7 não elegíveis têm esse padrão). Falha experimental registrada →
sustenta citando o registro; falha só operacional → neutra; sem falha → sem evidência."""),
    R("INC-D5", "incerteza", "documento", "llm", "A incerteza foi enfrentada, não contornada: se o time desviou do problema usando conhecimento disponível (workaround), não conta", "decisão técnica registrada", ["CRA SR&ED", "IE TDM §3.1"], ["evidencias/observacoes.csv", "evidencias/metodo.md#2"], "positive", "mean", prompt="""Nas observações e no §2, a barreira foi enfrentada ou contornada? Enfrentada com registro → sustenta;
contornada (workaround) → contrária; sem registro → sem evidência."""),
    R("INC-D6", "incerteza", "documento", "llm", "Integração de sistemas só tem incerteza se não era dedutível como combinar os componentes", "descrição do problema de integração", ["UK DSIT ¶29–30", "Frascati §2.73"], ["evidencias/metodo.md#2"], "positive", "mean", prompt="""Só para projetos de integração: o §2 descreve problema de integração não dedutível? Dedutível/padrão
estabelecido → contrária; não dedutível → sustenta; não é projeto de integração → sem evidência."""),
    R("INC-D7", "incerteza", "documento", "llm", "Protótipo/piloto testa conceito técnico arriscado; unidade pré-produção, produção-teste ou ajuste fino não é P&D", "finalidade do protótipo e o que foi testado", ["Frascati §2.18, §2.49–2.50, Tab. 2.3, §2.55–2.56"], ["evidencias/metodo.md#3"], "positive", "mean", status="aplicavel", status_reason=None, prompt="""Pouco aplicável na massa (quase não há protótipos físicos). Se o §3 descreve protótipo: conceito
técnico arriscado → sustenta; homologação/ajuste fino → contrária; sem protótipo → sem evidência."""),
    R("INC-D8", "incerteza", "documento", "regra", "Dá para delimitar início e fim da P&D: começa quando o trabalho sobre a incerteza começa; termina quando ela é resolvida, abandonada ou o conhecimento é codificado", "datas de início/fim da etapa incerta", ["UK DSIT ¶33–34", "HMRC GfC3 parte 2 passos 6–7", "FAQ MCTI P4(c)"], ["evidencias/cronologia.csv"], "positive", "mean", chk="CHK-TEMPO"),
    R("INC-D9", "incerteza", "documento", "llm+regra", "Correção de bugs, troubleshooting, otimização e ajuste fino que não mexem na tecnologia de base NÃO são incerteza; só a falha experimental indica incerteza", "natureza das tarefas; o que mudou entre v1 e v2 e por quê", ["Frascati §2.57, §2.72", "UK DSIT ¶14 ¶35", "Históricos PRJ01, 04, 09, 11, 12"], ["evidencias/metodo.md#2", "evidencias/cronologia.csv"], "negative", "mean", chk="CHK-FALHAS", prompt="""Use CHK-CONFIG + CHK-FALHAS (tools chk_resultado) — NÃO use natureza_informada_pela_equipe.
Falha operacional (parâmetro, permissão, cadastro, receita do fornecedor) → contrária (rotina).
Falha experimental → neutra para esta regra (conta na INC-D4)."""),
    R("INC-D10", "incerteza", "documento", "llm", "Incerteza de custo/tempo conta quando decorre da técnica (meta técnica como critério prévio); custo alto por motivo comercial não conta", "ligação entre a meta de custo e a questão técnica", ["Frascati §2.18", "IT MIMIT §1.1.3.3", "IE TDM §3.5", "Histórico PRJ18 latência ≤ 10%"], ["evidencias/metodo.md#2", "evidencias/metodo.md#3"], "positive", "mean", prompt="""No §2/§3, há meta técnica como critério prévio (ex.: latência ≤ 10%)? Meta técnica registrada →
sustenta citando-a; só custo comercial → contrária; nada → sem evidência."""),
    R("INC-D12", "incerteza", "documento", "regra+llm", "A incerteza só é 'investigada' quando a hipótese foi executada e confrontada com os comparadores conhecidos, com registro do resultado; só plano/diagrama → alegada", "ensaios por versão em medicoes.csv cobrindo a hipótese e os comparadores", ["Históricos PRJ02, 03, 13–16 × PRJ08, 10, 17"], ["evidencias/medicoes.csv", "evidencias/cronologia.csv"], "positive", "gate", chk="CHK-VERSOES", prompt="""Use CHK-VERSOES (tool chk_resultado): a hipótese do §2 tem versão com ensaio em medicoes.csv, ao
lado dos comparadores? Executada + registrada → sustenta; só plano/diagrama/memorando → contrária
('alegada, não verificável')."""),

    # ================= SISTEMATIZAÇÃO — 10 ativas =================
    R("SIS-D1", "sistematizacao", "documento", "regra", "O projeto tem objetivo, escopo e datas de início e fim", "termo de abertura, plano, campos 3.1.11–3.1.12", ["FAQ MCTI P4(d)-(e)", "Frascati §2.12", "IT MIMIT 2024 §1.1.3.4"], ["evidencias/cronologia.csv"], "positive", "mean", chk="CHK-TEMPO"),
    R("SIS-D2", "sistematizacao", "documento", "regra", "Há plano: etapas, cronograma, marcos e indicadores de sucesso definidos no início", "plano de projeto datado (Registro do problema e das referências ANTERIOR aos ensaios)", ["Guia MCTI 2020 Ap. B.4", "IE TDM §8.1(f)", "IT MIMIT §1.1.3.4"], ["evidencias/cronologia.csv"], "positive", "mean", chk="CHK-TEMPO"),
    R("SIS-D3", "sistematizacao", "documento", "regra", "Recursos próprios identificados: equipe adequada, orçamento e fonte de financiamento", "tabela de RH do projeto, currículos, orçamento aprovado", ["Frascati §2.19", "FORMP&D seção de RH", "IE TDM §8.1(g)-(h)"], ["atividades.csv"], "positive", "mean", status="parcial", status_reason="parcial: orçamento/dispêndios fora do escopo do guia; equipe só por função (responsavel_por_funcao), sem titulação"),
    R("SIS-D4", "sistematizacao", "documento", "regra", "Dispêndios rastreáveis ao projeto: contas contábeis específicas e apontamento de horas", "plano de contas, timesheets", ["Lei 11.196 art. 22 I", "Decreto 5.798 art. 10 I", "Portaria 9.563 art. 6º II", "FAQ MCTI P2"], [], "positive", "mean", status="na", status_reason="N/A — o guia do desafio exclui explicitamente horas/despesas/requisitos fiscais"),
    R("SIS-D5", "sistematizacao", "documento", "llm+regra", "A metodologia é de pesquisa/experimentação — hipótese → experimento → observação → avaliação → conclusão —, não gestão e NEM teste de aceite; comparadores nas mesmas entradas, referência fixada antes, critérios prévios", "descrição do método + protocolo (metodo.md#3), versões dos comparadores em cronologia.csv, ensaios em medicoes.csv", ["Guia MCTI 2020 §6.4", "FAQ MCTI P4", "CRA SR&ED", "AU R&DTI", "26 CFR §1.41-4(a)(5)", "IE TDM §3.6", "Históricos PRJ02, 13, 14, 16 × PRJ04, 09, 12"], ["evidencias/metodo.md#3", "evidencias/cronologia.csv", "evidencias/medicoes.csv"], "positive", "gate", chk="CHK-VERSOES", prompt="""Experimento × aceite. Use CHK-VERSOES (tool chk_resultado) e o §3: comparadores rodados nas
mesmas entradas? referência fixada antes? critérios definidos antes da rodada? Experimento → sustenta
citando o protocolo; roteiros com resultado esperado repetidos até passar (aceite) → contrária;
NÃO use natureza_informada_pela_equipe."""),
    R("SIS-D7", "sistematizacao", "documento", "llm", "Estão registrados os desvios: caminhos que falharam e por que se mudou de rumo", "registro de decisões, relatório de experimentos sem sucesso", ["IE TDM §3.1", "IT MIMIT §1.1.3.4"], ["evidencias/observacoes.csv", "evidencias/metodo.md#6"], "positive", "mean", chk="CHK-FALHAS", prompt="""Use CHK-FALHAS (tool chk_resultado) + observacoes.csv. Desvios/versões que falharam registrados →
sustenta citando o registro; sem desvio → neutra (aceite perfeito pode ser rotina — T13)."""),
    R("SIS-D10", "sistematizacao", "documento", "design", "A documentação fica guardada e acessível durante o prazo prescricional", "onde e por quanto tempo os documentos ficam guardados", ["Decreto 5.798 art. 14 §1º", "IE TDM §8.4"], [], "positive", "informativa", status="na", status_reason="N/A como input do pacote; satisfeita no output: dossiê versionado com autor/data (efeito do design da ferramenta)"),
    R("SIS-D12", "sistematizacao", "documento", "regra", "A execução está registrada por versão: cada versão alegada tem ensaio (ensaio_id) em medicoes.csv; parâmetros null/só entrega → parcial", "cronologia.csv × medicoes.csv × configuracao.json", ["Históricos PRJ08, 10, 17"], ["evidencias/cronologia.csv", "evidencias/medicoes.csv", "evidencias/configuracao.json"], "positive", "mean", chk="CHK-VERSOES"),
    R("SIS-D13", "sistematizacao", "documento", "llm", "Controles de desenho experimental são indícios fortes (não obrigatórios): estratos, repetições, ordem contrabalançada, atraso de rótulo", "metodo.md#3 e configuracao.json", ["Históricos PRJ02, 13, 15, 16"], ["evidencias/metodo.md#3", "evidencias/configuracao.json"], "positive", "mean", prompt="""No §3 e no configuracao.json, há controles de desenho experimental (estratos, repetições, ordem
contrabalançada, atraso de rótulo)? Presentes → sustenta citando; ausentes → neutra (não obrigatórios)."""),
    R("SIS-D14", "sistematizacao", "documento", "regra", "Contagem de entrega (quantas linhas/fichas) NÃO é desempenho e não prova execução; desempenho exige operação e base explícitas", "coluna natureza e taxa_percentual de resultados.csv", ["LEIA_ME", "Históricos PRJ08, 10, 17"], ["evidencias/resultados.csv"], "negative", "mean", chk="CHK-RECALC"),

    # ================= REPRODUTIBILIDADE — 9 ativas =================
    R("REP-D1", "reprodutibilidade", "documento", "regra+llm", "O conhecimento gerado está codificado num registro, não só no know-how", "relatório técnico datado", ["Frascati §2.20", "IPCTN 2020 Anexo I", "Nonaka 1994"], ["evidencias/metodo.md#4", "evidencias/configuracao.json"], "positive", "mean", prompt="""REGRA: configuracao.json presente e completo? LLM: o §4 'Parâmetros, versões e execução' traz
parâmetros concretos suficientes para repetir? Cite o trecho. Codificado → sustenta."""),
    R("REP-D2", "reprodutibilidade", "documento", "llm+regra", "O registro traz método, dados, configuração e resultados com detalhe suficiente para outro profissional repetir", "§4 + §5 Leitura e reconstrução + base recalculável", ["Frascati §2.20", "UK DSIT ¶34", "NASEM 2019"], ["evidencias/metodo.md#4", "evidencias/metodo.md#5"], "positive", "mean", chk="CHK-RECALC", prompt="""Use CHK-RECALC (tool chk_resultado) — a base é recalculável? — e leia o §5 'Leitura e reconstrução'.
Detalhe suficiente → sustenta citando o §5; base não recalculável → contrária."""),
    R("REP-D3", "reprodutibilidade", "documento", "regra", "Resultados negativos e hipóteses refutadas também estão documentados", "linhas de falha experimental em medicoes/resultados", ["Frascati §2.20", "Guia MCTI 2020 §6.2", "IT MIMIT §1.1.3.5", "T4"], ["evidencias/resultados.csv", "evidencias/medicoes.csv"], "positive", "mean", chk="CHK-FALHAS"),
    R("REP-D4", "reprodutibilidade", "documento", "regra", "Os artefatos estão preservados e versionados: especificação + configuracao.json + registros por versão (consistência cronologia ↔ medicoes ↔ configuracao)", "consistência dos identificadores de versão", ["Gundersen & Kjensmo 2018", "Wilkinson et al. 2016", "Histórico PRJ16"], ["evidencias/cronologia.csv", "evidencias/medicoes.csv", "evidencias/configuracao.json"], "positive", "mean", status="parcial", status_reason="parcial: o pacote não tem código executável; o artefato é especificação + configuracao.json + registros por versão", chk="CHK-VERSOES"),
    R("REP-D5", "reprodutibilidade", "documento", "regra", "Existe ao menos um mecanismo de transferência: patente, registro, publicação, documentação interna, treinamento", "nº de pedido/registro, DOI, documento interno", ["Frascati Tab. 2.1(d)", "Decreto 5.798 art. 2º II 'd'", "IT MIMIT §1.1.3.5"], [], "positive", "mean", status="na", status_reason="N/A no pacote — não há patentes, registros ou publicações; a 'Continuidade' (§7) não é transferência"),
    R("REP-D6", "reprodutibilidade", "documento", "regra", "O registro é coerente com a sistematização: a cadeia plano → resultado fecha (cronologia.fonte → metodo.md#n; resultados.fonte → medicoes.csv#Snn)", "grafo de referências nativo do pacote", ["IT MIMIT §1.1.3.5", "REP-D6 da nota"], ["evidencias/cronologia.csv", "evidencias/resultados.csv"], "positive", "mean", chk="CHK-VERSOES"),
    R("REP-D7", "reprodutibilidade", "documento", "llm+regra", "A conclusão declara o limite de escopo: excluído desde o início (sem ressalva) × lacuna dentro da pretensão (ressalva)", "metodo.md#6/#7, revisao_tecnica.md, flags ..._executado: false", ["Históricos PRJ03, 14, 15, 16 × PRJ05, 06, 07, 18", "GUIA_DO_PARTICIPANTE"], ["evidencias/metodo.md#6", "evidencias/metodo.md#7", "evidencias/revisao_tecnica.md", "evidencias/configuracao.json"], "positive", "gate", chk="CHK-ESCOPO", prompt="""Use CHK-ESCOPO (tool chk_resultado) + §6/§7. Limite excluído desde o início → neutra (sem
ressalva). Lacuna dentro da pretensão original → contrária com a ressalva técnica concreta
(recorte + limitação + evidência necessária)."""),
    R("REP-D8", "reprodutibilidade", "documento", "llm", "Documentação completa de uma configuração reproduz a configuração, não um conhecimento novo", "natureza do que está documentado", ["Históricos PRJ01, 04, 09, 11, 12, 19, 20"], ["evidencias/metodo.md#4", "evidencias/configuracao.json"], "negative", "gate", chk="CHK-CONFIG", prompt="""Use CHK-CONFIG (tool chk_resultado): o que está documentado é a configuração de um produto?
Documentação de configuração → contrária ('documentada para a configuração')."""),
    R("REP-D9", "reprodutibilidade", "documento", "regra", "Os números são recalculáveis do registro primário (medicoes.csv → resultados.csv) e ligados a ensaio e versão", "recálculo a partir de medicoes.csv", ["LEIA_ME", "Históricos PRJ02, 13, 15"], ["evidencias/medicoes.csv", "evidencias/resultados.csv"], "positive", "mean", chk="CHK-RECALC"),

    # ================= ABSORVIDAS (marcador — não executam) =================
    R("NOV-D7", "novidade", "documento", "regra", "Absorvida → T2 (plurianual)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em T2 (plurianual)", absorbed_into="T2"),
    R("NOV-D9", "novidade", "documento", "regra", "Absorvida → NOV-D2 (estado da arte)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em NOV-D2", absorbed_into="NOV-D2"),
    R("CRI-D9", "criatividade", "documento", "regra", "Absorvida → CRI-D5 (mudança não rotineira)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em CRI-D5", absorbed_into="CRI-D5"),
    R("INC-D11", "incerteza", "documento", "regra", "Absorvida → INC-D9 (falha operacional)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em INC-D9", absorbed_into="INC-D9"),
    R("INC-D13", "incerteza", "documento", "regra", "Absorvida → INC-D1 (incerteza técnica)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em INC-D1", absorbed_into="INC-D1"),
    R("SIS-D6", "sistematizacao", "documento", "regra", "Absorvida → T5 (contemporâneo > reconstruído)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em T5", absorbed_into="T5"),
    R("SIS-D8", "sistematizacao", "documento", "regra", "Absorvida → T2 (plurianual)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em T2", absorbed_into="T2"),
    R("SIS-D9", "sistematizacao", "documento", "regra", "Absorvida → CRI-D3 (pesquisador) e SIS-D3 (equipe)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em CRI-D3 + SIS-D3", absorbed_into="CRI-D3"),
    R("SIS-D11", "sistematizacao", "documento", "regra", "Absorvida → SIS-D5 (metodologia experimental)", "—", ["Revisão de redundância 08/10/2026"], [], "positive", "informativa", status="absorvida", status_reason="Absorvida em SIS-D5", absorbed_into="SIS-D5"),

    # ================= TRANSVERSAIS (T1–T15) =================
    R("T1", "transversal", "transversal", "regra", "Critérios cumulativos, verificados por projeto", "unidade = pasta do projeto", ["Tabela estado → classe"], [], "positive", "informativa", status="aplicavel"),
    R("T2", "transversal", "transversal", "regra", "Plurianual: cada ano-base separado", "flag se a cronologia atravessar mais de um ano-base", ["Revisão 08/10"], ["evidencias/cronologia.csv"], "positive", "informativa", status="na", status_reason="N/A no pacote (janela única por projeto) — flag se a cronologia atravessar mais de um ano-base"),
    R("T3", "transversal", "transversal", "regra", "Comparação sempre na data de início", "CHK-TEMPO", ["Fluxo do Backend passo 3"], ["evidencias/cronologia.csv"], "positive", "informativa", chk="CHK-TEMPO"),
    R("T4", "transversal", "transversal", "regra", "Resultado negativo não desqualifica", "CHK-FALHAS: falha experimental com polaridade positiva", ["Histórico PRJ18"], ["evidencias/resultados.csv"], "positive", "informativa", chk="CHK-FALHAS"),
    R("T5", "transversal", "transversal", "regra", "Contemporâneo > reconstruído", "CHK-TEMPO: datas progressivas; documento reconstruído no fim → flag", ["SIS-D6 absorvida"], ["evidencias/cronologia.csv"], "positive", "informativa", chk="CHK-TEMPO"),
    R("T6", "transversal", "transversal", "design", "Query web sem dado sigiloso (sanitização)", "queries sanitizadas + log original × sanitizada", ["Módulo web"], [], "positive", "informativa", status="aplicavel"),
    R("T7", "transversal", "transversal", "design", "Ferramenta sinaliza, analista decide", "nó de evidência sempre com citação; combinação mista vai ao analista", ["Design"], [], "positive", "informativa", status="aplicavel"),
    R("T8", "transversal", "transversal", "design", "Software só é P&D com avanço + incerteza sistemática", "gate de domínio: NOV-D5 (exclusões) + INC-D9 (rotina) implementam", ["Frascati §2.68"], ["evidencias/metodo.md#2"], "positive", "informativa", status="aplicavel"),
    R("T9", "transversal", "transversal", "regra", "Hierarquia de prova; entrevista nunca sustenta sozinha", "nós vindos da transcrição levam natureza=depoimento e não fecham critério", ["Camada 1"], ["transcricao_entrevista_tecnica.pdf"], "positive", "informativa", chk="CHK-DIVERG"),
    R("T10", "transversal", "transversal", "regra", "Divergência entrevista × registro registrada", "CHK-DIVERG", ["T10"], ["transcricao_entrevista_tecnica.pdf", "evidencias/resultados.csv"], "positive", "informativa", chk="CHK-DIVERG"),
    R("T11", "transversal", "transversal", "regra", "Versão, escopo, unidade, denominador; operação e base explícitas", "CHK-RECALC + CHK-DIVERG antes de qualquer comparação numérica", ["Camada 1"], ["evidencias/resultados.csv"], "positive", "informativa", chk="CHK-RECALC"),
    R("T12", "transversal", "transversal", "regra", "'Localizada' = presente, não provado", "tabela de disponibilidade probatória (inventário × conteúdo real)", ["Camada 1"], ["inventario_evidencias.csv"], "positive", "informativa"),
    R("T13", "transversal", "transversal", "design", "Aceite perfeito pode ser rotina; natureza declarada não decide", "nenhuma regra usa natureza_informada_pela_equipe, nº de testes ou taxa de aprovação como sinal", ["Design"], ["atividades.csv"], "positive", "informativa", status="aplicavel"),
    R("T14", "transversal", "transversal", "design", "Evidências favoráveis, contrárias, ausentes e contraditórias", "cada nó do grafo tem polaridade; regra sem evidência sai como 'ausente', nunca some", ["Design"], [], "positive", "informativa", status="aplicavel"),
    R("T15", "transversal", "transversal", "design", "Históricos = calibração, não gabarito por semelhança", "PRJ01–20 servem para testar a ferramenta contra o gabarito", ["Design"], [], "positive", "informativa", status="aplicavel"),

    # ================= CHECAGENS COMPARTILHADAS (CHK-*) =================
    R("CHK-TEMPO", "compartilhada", "shared", "regra", "Linha do tempo, data de referência, ordem hipótese→ensaios, datas progressivas", "cronologia.csv + datas de medicoes/configuracao", ["Camada 1"], ["evidencias/cronologia.csv"], "positive", "informativa"),
    R("CHK-RECALC", "compartilhada", "shared", "regra", "Recompute medicoes → resultados (contagem, diferenca_maior_menor, percentil_95, indicador_precalculado, valor_observado); batendo/não batendo/vazio; soma só no mesmo ensaio", "medicoes.csv + resultados.csv", ["Camada 1"], ["evidencias/medicoes.csv", "evidencias/resultados.csv"], "positive", "informativa"),
    R("CHK-VERSOES", "compartilhada", "shared", "regra", "Consistência cronologia ↔ medicoes ↔ configuracao.json; parâmetros-chave não nulos; comparadores do §1", "cronologia.csv, medicoes.csv, configuracao.json, metodo.md §1–§4", ["Camada 1"], ["evidencias/cronologia.csv", "evidencias/medicoes.csv", "evidencias/configuracao.json"], "positive", "informativa"),
    R("CHK-FALHAS", "compartilhada", "shared", "regra", "Versões com falha ou piora e o tipo: operacional × experimental", "resultados.csv por versão, observacoes.csv, metodo.md §2/§6", ["Camada 1"], ["evidencias/resultados.csv", "evidencias/observacoes.csv"], "positive", "informativa"),
    R("CHK-CONFIG", "compartilhada", "shared", "regra", "A referência anterior (manual/catálogo/produto contratado, datado antes) já fornece a função? O mecanismo é configurar/ativar/mapear/ajustar dentro da faixa suportada?", "metodo.md §1 e §2, configuracao.json, cronologia.csv", ["Camada 1"], ["evidencias/metodo.md#1", "evidencias/metodo.md#2", "evidencias/configuracao.json"], "positive", "informativa"),
    R("CHK-ESCOPO", "compartilhada", "shared", "regra", "Limite da conclusão: excluído desde o início × lacuna dentro da pretensão (flags ..._executado: false)", "metodo.md §6/§7, revisao_tecnica.md, configuracao.json", ["Camada 1"], ["evidencias/metodo.md#6", "evidencias/revisao_tecnica.md", "evidencias/configuracao.json"], "positive", "informativa"),
    R("CHK-DIVERG", "compartilhada", "shared", "regra", "Números da transcrição × registros (mesma versão, ensaio, denominador)", "transcricao_entrevista_tecnica.pdf, resultados.csv, medicoes.csv", ["Camada 1"], ["transcricao_entrevista_tecnica.pdf", "evidencias/resultados.csv"], "positive", "informativa"),
]


def main() -> None:
    data = {
        "catalog_version": "1.0.0",
        "artifacts": [{"id": k, "nature": v} for k, v in ARTIFACTS.items()],
        "rules": RULES,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)
    print(f"OK — {len(RULES)} regras -> {OUT}")


if __name__ == "__main__":
    main()