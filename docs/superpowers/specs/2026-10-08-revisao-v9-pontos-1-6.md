# Design — Melhorias V9.1: sinais de rotina, consistência, fundamentação, CHK citável, web aterrado

Data: 2026-10-08
Status: planejado (revisão da análise e2e do PRJ01 contra o gabarito `historicos_classificados.md`)
Branch alvo: `feature/models-and-modules`
Superpowers: spec aprovada pelo usuário no fluxo (planejar → implementar)

## 1. Contexto

A e2e do PRJ01 produziu o grafo `data/graphs/PRJ01/v1` (244 nós / 283 arestas). Contra o
gabarito (PRJ01 = **Não elegível**: novidade NÃO DEMONSTRADA, criatividade NÃO DEMONSTRADA,
incerteza NÃO CARACTERIZADA), a distribuição de polaridade por critério foi:

| Critério | sustenta | contraria | Gabarito | Veredito |
|---|---|---|---|---|
| NOV | 5 | 7 | NÃO DEMONSTRADA | ✓ |
| CRI | 9 | 2 | NÃO DEMONSTRADA | ✗ |
| INC | 11 | 4 | NÃO CARACTERIZADA | ✗ |

Furos identificados (com exemplo real do grafo v1):

1. **INC-D2 sustentado pela pergunta "Como aplicar idempotência conhecida ao reenvio…"**
   — a pergunta que JÁ NOMEIA a solução é sinal de rotina no gabarito (Padrão de Análise §3),
   não de incerteza. A regra derivada não está codificada.
2. **CRI-D10 sustenta "acoplamento inovador" citando o §1 que descreve o manual BARR-2**
   enquanto NOV-D4/NOV-D10 contratam o mesmo texto — polaridades contraditórias convivendo,
   sem checagem cruzada entre critérios.
3. **Justificativa especulativa passou pelo gate** ("pode gerar comportamento inesperado,
   caracterizando risco" — INC-D1): o gate só valida o quote literal, não a ancoragem da
   justificativa.
4. **~15 gaps falsos mecânicos**: o agente citou saídas de checagem como fonte
   (`CHK-VERSOES`, `chk_resultado(CHK-CONFIG)`) — âncora inexistente → gate derrubou.
   As CHKs precisam ser fontes citáveis de primeira classe.
5. **Web quase morto**: NOV-W7 registra falha de autorização; queries salvas incluem lixo
   ("open problem in quantum error correction", "Internet of Things Wikipedia", query literal
   "NOV-W3", rule_id órfão "list_repo") — geração de query sem aterramento no domínio.
6. **2 gaps por parse**: "resposta não era JSON válido" (INC-W3, SIS-D1) sem checagem de
   schema antes do retry; `manifest_hash: null` no meta.

## 2. Calibração determinística (medida nos 20 históricos, 2026-10-08)

| Detector | Dispara em | Falsos positivos |
|---|---|---|
| **A. marcador de solução conhecida na pergunta** (`conhecida/os`, `contratado/a`, `existente`, `disponível` no texto da `Pergunta:`) | PRJ01, PRJ12 — exatamente os 2 nomeados no gabarito | 0 / 18 |
| **B. assinaturas literais de rotina no §2** (`nenhum algoritmo`, `já admitida`, `receita do fornecedor`, `modo sombra`/`shadow=true`) | PRJ01, PRJ12, PRJ20 | 0 |
| **C. verbos de configuração** (já em `CHK-CONFIG`) | `funcao_ja_fornecida=True` nos 7 não elegíveis; `False` em PRJ02/03/13/18 | 0 |
| Caso cego documentado | PRJ11 (`Aplicar mapeamento…`, referência é dicionário): detector A/B/C não pegam sozinhos; compensado pela regra LLM CRI-D5/NOV-D10 + prompt novo da INC-D2 | — |

## 3. Decisões

| # | Decisão | Escolha |
|---|---|---|
| 1 | Onde codificar os sinais de rotina | CHK-PERGUNTA nova (determinística) + prompt da INC-D2 e INC-D9; CHK-FALHAS ganha direção da métrica (menor-é-melhor para falsos/erros/latência) |
| 2 | Consistência entre critérios | Pós-pass DETERMINÍSTICO no grafo (código, não LLM): trecho marcado "contido na referência anterior" (NOV contraria) rebaixa sustenta de CRI/INC na MESMA fonte; rebaixamento é auditável (`polaridade_original` + gap na regra). Incerteza do tipo (operacional × experimental) continua no especialista |
| 3 | Segundo gate de fundamentação | Determinístico: justificativa com modal especulativo ("pode gerar", "possivelmente"…) SEM conector de ancoragem ("o trecho mostra", "porque", "cita", "demonstra"…) é rejeitada e segue o fluxo de retry/gap existente |
| 4 | CHK citável | Cada CHK vira fragmento `chk:CHK-X` (texto = mesmo JSON servido pela tool), validável pelo gate de citação; natureza forçada "derivado"; excluído do `buscar_em_arquivos` |
| 5 | Web | (a) `web_search/web_fetch` async via `get_client()` (leva auth/host do client); (b) closure por agente com `rule_id` da regra corrente; (c) query sem termo do domínio do projeto é devolvida com erro instrutivo antes de sair |
| 6 | Robustez de parse | `_validate_schema` (campos obrigatórios, polaridade do vocabulário, `evidencias=[]` exige motivo) entra no ciclo de retry; `manifest_hash` = sha256 do manifest de arquivos |

## 4. Arquivos

| Arquivo | Mudança |
|---|---|
| `src/ai_microservice/checks/pergunta.py` | NOVO — CHK-PERGUNTA: extrai pergunta(s) de atividades.csv/xlsx, aplica regex de marcador de solução conhecida |
| `src/ai_microservice/checks/falhas.py` | PATCH — direção da métrica (menor-é-melhor p/ falso/erro/falha/latência/perda); piora só quando a direção inverte |
| `src/ai_microservice/checks/runner.py` | PATCH — inclui CHK-PERGUNTA |
| `src/ai_microservice/gate.py` | PATCH — `valida_justificativa(justificativa)` |
| `src/ai_microservice/agents/consistency.py` | NOVO — pós-pass de consistência (ponto 2) |
| `src/ai_microservice/agents/criterion.py` | PATCH — CHK como fonte citável; fundamentação no `_validate_evidence`; coerção de natureza p/ CHK; `_validate_schema`; `rule_id` no web_search; `domain_terms` |
| `src/ai_microservice/tools/web.py` | PATCH — async via `get_client()`; mantém sanitize/log |
| `src/ai_microservice/tools/file_search.py` | PATCH — `extract_domain_terms(fragments)` |
| `src/ai_microservice/agents/orchestrator.py` | PATCH — hook do pós-pass após `gather`; `manifest_hash`; `domain_terms` calculados 1× |
| `catalog/rules.yaml` | PATCH — INC-D2 recebe `chk: CHK-PERGUNTA` + prompt com regra da pergunta-nomeia-solução |
| `catalog/handbooks/{INC,NOV,CRI}.md` | PATCH — armadilhas: pergunta-nomeia-solução; trecho da referência não prova criatividade; justificativa deve ancorar no quote |
| `tests/test_melhorias_v9.py` | NOVO — testes dos pontos 1–6 |
| `tests/test_catalog.py` | PATCH — 8 compartilhadas, id CHK-PERGUNTA na lista |

## 5. Detalhe por ponto

### Ponto 1 — Sinais de rotina codificados

`CHK-PERGUNTA` (determinístico):
- coleta `resultado_ou_saida` prefixado `Pergunta:` dos fragmentos de `atividades.csv` e
  `atividades.xlsx` (dedupe por texto — o xlsx reflete o csv);
- marcador = regex `\b(conhecid[ao]s?|existente[s]?|contratad[oa]s?|dispon[íi]ve[lis]?|admitid[ao]s? pelo produto)\b`;
- saída: `{"pergunta": str, "marcador": str|None, "aplica_solucao_conhecida": bool, "fonte": âncora}`.

`INC-D2` (catálogo): `chk: CHK-PERGUNTA` e prompt acrescido da regra derivada:
> Pergunta que JÁ NOMEIA a solução conhecida ("aplicar idempotência **conhecida**", "integrar
> ao cofre **contratado**") é sinal de rotina (históricos PRJ01/PRJ12) → **contrária**, mesmo
> havendo padrão `Pergunta:`; pergunta técnica aberta → sustenta.

`CHK-FALHAS` — correção de direção: métricas com nome contendo falso(s), erro(s), falha(s),
latência, perda, piora são MENOR-É-MELHOR; a lista de `pioras` só marca trocas que pioram NA
direção correta. Adiciona `direcao` por métrica ao dict de saída.

### Ponto 2 — Pós-pass de consistência (determinístico, auditorável)

`run_consistency(builder, checks)` após os 5 especialistas:

- **Regra da referência anterior**: evidências `contraria` em regras NOV cuja justificativa
  contenha marcador de contenção ("já fornece", "já era fornecida", "anterior", "adaptação de
  tecnologia", "já existia", "já estava") marcam seus `fonte` como "trecho da referência que
  contém a função".
- Toda evidência `sustenta` de CRI/INC com `fonte` nesse conjunto é rebaixada:
  `polaridade → neutra`, props ganham `polaridade_original` e `ajuste_consistencia` (motivo,
  citando a regra NOV que contratou); a regra cuja evidência foi rebaixada recebe gap
  ("ajuste de consistência").
- **Regra INC-D2 × CHK-PERGUNTA**: se `aplica_solucao_conhecida=True` e existe evidência
  `sustenta` em `regra:INC-D2` cujo quote contém o texto da pergunta → rebaixada para
  `contraria` com o mesmo registro de auditoria.
- Não rebaixa quando não há marcador, nem evidência em fonte diferente. Nunca apaga: polaridade
  original fica em props (T7 — ferramenta sinaliza, analista decide).
- Contagem de ajustes vai para `meta["consistencia"]`.

### Ponto 3 — Gate de fundamentação

`valida_justificativa(justificativa) -> tuple[bool, str]`:
- < 6 palavras → rejeita ("justificativa insuficiente");
- contém modal especulativo (`pode gerar`, `pode caracterizar`, `pode indicar`, `pode houver`,
  `possivelmente`, `talvez`, `provavelmente`, `aparentemente`, `improvável que`) E nenhum
  conector de ancoragem (`o trecho`, `o texto`, `o registro`, `cita`, `descreve`, `afirma`,
  `declara`, `demonstra`, `porque`, `pois`, `indica que`, `informa`, `mostra`) → rejeita
  ("especulativa sem ancoragem no quote");
- caso contrário ok. Falha segue o MESMO fluxo do gate de citação (retry 1× → gap).

### Ponto 4 — CHK como fonte citável

- `CriterionAgent` constrói `self._chk_texts = {chk_id: json.dumps(res, ensure_ascii=False,
  indent=2)[:6000]}` uma vez (mesma string na tool e na validação — sem divergência de
  truncamento); `chk_resultado` devolve esse texto.
- `_validate_evidence`: fonte `chk:X` → válido se `quote_in_source(quote, self._chk_texts[X])`;
  `_record` força `natureza="derivado"` nessas evidências.
- Fonte `chk:X` vira nó `fonte` normal (âncora preservada) — visível no viz.
- `buscar_em_arquivos` contina a buscar SÓ fragmentos do pacote (CHK fora) — sem poluição.

### Ponto 5 — Web com auth + aterrado no domínio

- `WebTools.web_search/web_fetch` viram async e chamam `await get_client().web_search(...)` /
  `web_fetch(url=...)` — o client carrega host e key (falha de auth permanece como
  `ERRO_WEB` auditável, mas agora com o auth correto).
- O `_make_tools` do agente envolve o `web_search` em closure que: (1) passa
  `rule_id=self._current_rule_id` (setado em `process_rule` — sem compartilhar estado
  mutável entre agentes); (2) valida aterramento: `domain_terms` (tokens ≥5 letras extraídos
  de metodo.md#2, medicoes.csv e resultados.csv, top 25 por frequência, determinístico);
  query sem nenhum termo do domínio → `ERRO_QUERY: … inclua ao menos um destes termos: …`
  (não sai da máquina, não loga como rodada válida).
- Queries vazias após sanitização continuam bloqueadas (`NADA_BUSCADO`).

### Ponto 6 — Parse com validação de schema + manifest_hash

- `_validate_schema(parsed)` em `criterion.py`: objeto; `evidencias` lista (ou ausente com
  `sem_evidencia_motivo`); cada evidência com `fonte/quote/polaridade/justificativa`
  preenchidos; `polaridade ∈ {sustenta, contraria, neutra}`; `evidencias=[]` exige
  `sem_evidencia_motivo`. Erro de schema entra no mesmo ciclo de 2 tentativas; depois disso,
  gap `rejeitada_gate` com o motivo — nunca silêncio.
- Orchestrator: `manifest_hash = sha256(json.dumps(manifest["files"], sort_keys=True))` →
  meta (corrige `null`).

## 6. Fora do escopo desta iteração

- Cálculo de estado por critério → classe (próxima iteração; a calibração da tabela §1 é o passo seguinte).
- Retry do gate de citação > 1 tentativa; LLM adversarial para fundamentação (a versão é heurística determinística).
- MongoDB, parecer, chatbot (conforme spec principal).

## 7. Testes (novos, `tests/test_melhorias_v9.py`)

- CHK-PERGUNTA: dispara em PRJ01 (`idempotência conhecida`) e PRJ12 (`contratado`); não
  dispara em PRJ02/03/13 (perguntas abertas); dedupe csv/xlsx.
- CHK-FALHAS direção: PRJ13 "falsos alertas entre legítimas" 7,8→5,5 NÃO deve constar em `pioras`.
- Fundamentação: especulativa sem ancoragem rejeitada; causal ok; <6 palavras rejeitada.
- Consistência: NOV contraria com marcador rebaixa sustenta de CRI/INC na mesma fonte
  (com `polaridade_original` preservado); não rebaixa em fonte diferente nem sem marcador;
  INC-D2 × CHK-PERGUNTA vira contraria.
- CHK citável: `chk:CHK-CONFIG` aceita quote do JSON da checagem, rejeita quote inventado;
  natureza forçada `derivado`.
- Schema: falta polaridade → erro; polaridade inválida → erro; `evidencias=[]` sem motivo → erro.
- Queries: termo do domínio presente passa; query sem termo → erro instrutivo; log registra
  regra corrente (`rule_id` ≠ None).
- `_validate_evidence` mantém contrato: âncora de fragmento e http continuam como antes.

## 8. Critérios de aceite

1. Suíte verde: `.venv/bin/python -m pytest tests/ -x -q` (sem marcador `llm`).
2. E2e real no PRJ01 (`POST /analyze`) produz v2: (a) zero gap `âncora inexistente: CHK-*`;
   (b) evidências de CRI/INC que citam §1 (manual BARR-2) rebaixadas com `ajuste_consistencia`;
   (c) INC-D2 sobre a pergunta do PRJ01 sai `contraria`; (d) toda query web tem `rule_id`
   e termo do domínio; (e) `manifest_hash` não nulo.
3. Classe derivável do grafo v2 deve tender a "Não elegível" (contagem CRI/INC sustenta ≤ contraria
   nos critérios-chave) — verificação manual na calibração.