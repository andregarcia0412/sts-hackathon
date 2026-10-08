🗺️ Versão em diagramas: [[Fluxo do Backend Visual]]
🤖 Arquitetura de agentes: [[STS 2026 — Arquitetura de Agentes]]

## 1. Módulo de Extração
### Requisitos para tarefa concluída:

Converte o pacote do projeto no **JSON canônico**, a entrada única de todos os outros módulos. Decisões em [[STS 2026 — Decisões do Modelo e do Back#Módulo de conversão (entrada do modelo)]]; camadas 0 e 1 de [[organizacao-dados-por-criterio]]; mapa dos 14 arquivos em [[STS 2026 — Mapa dos Casos para Análise]].

#### Ingestão

- [ ] Aceitar pdf, markdown, csv, xlsx e json;
- [ ] Pacote imutável: gerar um manifest por projeto (caminho + hash de cada arquivo) e nunca alterar o original;
- [ ] Identificar o tipo de arquivo pelo conteúdo, não pelo nome (títulos dos PDFs/MDs, cabeçalho dos CSVs, chaves do JSON); o `inventario_evidencias.csv` liga cada arquivo ao seu ID `EV`;

#### Conversão determinística (sem LLM quando o arquivo é reconhecido)

- [ ] Quebrar cada arquivo em fragmentos com ID estável, que são a unidade de citação (`PRJ21-EV01#referencia_anterior`, `PRJ21-CR01`, `PRJ21-S01`), guardando arquivo, página/linha, texto literal e natureza (síntese, depoimento, registro primário, derivado);
- [ ] Mapear as seções fixas: dossiê (6), registro técnico (6), entrevista (7 perguntas, em ordem embaralhada), `metodo.md` (§1–§7);
- [ ] Parser de CSV/XLSX: célula vazia vira `null`, nunca `0` (vazio ≠ zero); XLSX tem cabeçalho na linha 5;
- [ ] Montar a linha do tempo (`cronologia.csv` + datas de `medicoes`/`configuracao`) e fixar a data de referência do projeto (NOV-W1, T3), conferindo com "corte − semanas" do cabeçalho do dossiê;

#### Contexto para os modelos de pesquisa

- [ ] Gerar o sumário do projeto num JSON de schema fixo: elemento novo (`metodo.md#2`), referência anterior (`#1`), barreira/pergunta (dossiê + `atividades.csv`), produtos/ferramentas citados, data de referência. É a entrada do módulo de pesquisa na web;
- [ ] A LLM só extrai e rotula, nunca reescreve: cada campo do sumário carrega a citação literal + ID do fragmento, e um campo sem citação que exista no fragmento é rejeitado (gate de citação);
- [ ] Marcar a entrevista como depoimento: entra no JSON, mas nunca como evidência;

#### Arquivo não reconhecido

- [ ] A LLM classifica o tipo e mapeia as seções para as chaves fixas → a análise roda → o front mostra "pendente de validação" → o analista confirma ou corrige → se corrigir, reconverte e refaz a análise;

#### Persistência

- [ ] Salvar no MongoDB o JSON canônico, o manifest e a versão do conversor/modelo usado (rastreabilidade);


## 2. Módulo de Pesquisa na Web
### Requisitos para tarefa concluída:

Cobre as regras `-W` de [[Novidade — Regras de Validação|Novidade]] (NOV-W1…W8), [[Criatividade — Regras de Validação|Criatividade]] (CRI-W1…W5) e [[Incerteza — Regras de Validação|Incerteza]] (INC-W1…W4). O que já existe no módulo de Novidade está em [[STS 2026 — Decisões do Modelo e do Back]]; a organização dos dados está em [[organizacao-dados-por-criterio]].

#### Entrada e preparação

- [ ] Receber o JSON canônico do módulo de extração (não os arquivos brutos): elemento novo (`metodo.md#2`), referência anterior (`#1`), barreira/pergunta (dossiê + `atividades.csv` "Pergunta: …") e produtos/ferramentas citados;
- [ ] Data de referência por duas fontes: "corte − semanas" do cabeçalho do dossiê × 1º evento da `cronologia.csv`; se divergirem, gerar flag (NOV-W1, T3);
- [ ] Decompor o elemento novo em características atômicas (como reivindicações de patente), base para NOV-W3 e CRI-W1;

#### Geração de queries (uma família por regra)

- [ ] Cada query marcada com a regra que serve: NOV → mecanismo; INC-W1/W2 → solução da barreira (não o produto); CRI-W2 → a configuração em doc oficial/tutorial; CRI-W5/INC-W3 → problema relatado como em aberto;
- [ ] Queries em PT e EN, com sinônimos técnicos e classes IPC/CPC (G06F, H04L, G06Q 40) — WIPO 946;
- [ ] Sanitização com lista de bloqueio (PRJxx, nomes de equipe, códigos internos, números de resultado) e log da query original × sanitizada (T6);
- [ ] Buscar também evidência a favor (problema em aberto, contra o consenso) para não ter viés de rejeição (CRI-W5, CRI-D6);
- [ ] As queries devem ser armazenadas no banco de dados para rastreabilidade

#### Frentes e bases

- [ ] 4ª frente: documentação técnica e prática padrão — docs oficiais de fornecedores/frameworks, guias de arquitetura de cloud, RFC/IETF, OWASP/NIST, GitHub (repos e issues), Stack Overflow. Pega o CRI-W2, principal gatilho dos casos "não elegível" (ex.: PRJ21, circuit breaker documentado no Resilience4j/Istio);
- [ ] Frente de mercado focada no setor: blogs de engenharia de bancos/fintechs, palestras, cases de fornecedor (NOV-W4);
- [ ] Buscar a solução vendida como serviço ou consultoria — se estava à venda, não havia incerteza (INC-W2);
- [ ] Incluir bases BR: BDTD, SciELO, INPI (ver [[Regras de Validação — Referências#Bases e APIs de busca]]);

#### Tratamento temporal

- [ ] Filtro de data dentro de cada API (`to_publication_date` no OpenAlex, `before:priority` no Google Patents);
- [ ] Datar páginas web pela 1ª captura na Wayback Machine (CDX API) — NOV-W7. Sem data → "data indeterminada" (não conta como anterior nem posterior);
- [ ] Achados posteriores à data de referência não são descartados: ficam separados, rotulados "não é estado da arte", e alimentam o NOV-W6;
- [ ] Usar a documentação na versão vigente na data de referência (snapshot da Wayback);

#### Avaliação dos achados

- [ ] Claim chart do documento mais próximo (característica a característica: presente / parcial / ausente). Um único documento com cobertura total → NOV-W3 negativo; combinação de 2+ documentos vai para CRI-W1/W3 (não-obviedade), não para novidade (INPI: um documento por vez). Resolve o ponto em aberto da "evidência decisiva";
- [ ] Classificar se o achado descreve o *método* ou só o *resultado* — página de marketing sem o "como" preserva a novidade (NOV-W5);
- [ ] Encadear CRI-W1 ao NOV-W3: reaproveitar o documento mais próximo, derivar o problema técnico objetivo e gerar a justificativa de não-obviedade como sinal, não veredito (T7);
- [ ] Estimar o TRL pelo tipo de achado (só artigo ≈ 2–4; biblioteca open-source madura ≈ 7–8; produto comercial = 9), com justificativa (INC-W4);
- [ ] Comparar o resultado da web com o §1 do projeto: se a web achar algo mais próximo que o citado pela equipe → sinal "estado da arte declarado incompleto" para o NOV-D2;

#### Robustez e rastreabilidade

- [ ] Teste de recall ("known item"): a busca precisa achar a técnica pública que o próprio §1 diz já existir; se não achar → flag de cobertura fraca;
- [ ] Ausência de achado ≠ prova de novidade: registrar "nada encontrado após N bases × M queries", com peso menor. Web fora do ar → regras W "não executadas", nunca zero (vazio ≠ zero);
- [ ] Critério de parada por saturação (novas queries sem achado relevante novo), dentro de um teto de orçamento, com o motivo da parada no log (PRISMA-S, NOV-W8);
- [ ] Deduplicar por DOI e por família de patente — a mesma fonte conta uma vez por regra;
- [ ] Snapshot de cada fonte (URL, data de captura, hash do conteúdo, trecho citado) + cache e temperature 0, para reexecução dar o mesmo resultado;
- [ ] Conteúdo das páginas tratado como dado, nunca como instrução para a LLM resumidora (defesa contra prompt injection);
- [ ] Registrar no grafo as arestas query → resultado → evidência → regra;
- [ ] Analista pode marcar achado como irrelevante ou incluir URL manualmente (a URL manual também passa pelo NOV-W7) e a nota é recalculada;
- [ ] Calibrar com os históricos PRJ01–20: as regras W concordam com o gabarito?

## 3. Pesquisa por Documento
### Requisitos para tarefa concluída:

Fluxo: regra a ser validada → manifesto/roteamento indica o documento e a seção → achar a evidência para a regra no documento. Cobre as regras `-D` dos 5 critérios (NOV, CRI, INC, [[Sistematização — Regras de Validação|SIS]], [[Reprodutibilidade — Regras de Validação|REP]]) e as transversais. O mapa "qual dado alimenta qual regra" está na Parte 3 de [[organizacao-dados-por-criterio]]; as armadilhas dos casos estão em [[STS 2026 — Mapa dos Casos para Análise]].

#### Entrada e roteamento

- [ ] Reutilizar o JSON canônico da tarefa 1 (fragmentos com ID estável), sem reprocessar os arquivos;
- [ ] Tabela de roteamento regra → artefato/seção → modo (REGRA / LLM / REGRA+LLM), lida do catálogo de regras (seção 8) e tirada da Parte 3 de [[organizacao-dados-por-criterio]]. Ex.: NOV-D1 → `metodo.md#2` (LLM); CRI-D3 → `atividades.csv` coluna `responsavel_por_funcao` (REGRA);
- [ ] Regras N/A no pacote (NOV-D7, SIS-D4, SIS-D8, SIS-D10, T2) e parciais (SIS-D3, SIS-D9, REP-D4) saem com o motivo escrito, nunca em silêncio;

#### Regras determinísticas (modo REGRA, rodam antes das de LLM)

- [ ] Recompute de `resultados.csv` × `medicoes.csv` por operação (`contagem`, `diferenca_maior_menor` — base não divide —, `percentil_95` pelo histograma, `indicador_precalculado`, `valor_observado`), com saída batendo / não batendo / vazio. Somar só dentro do mesmo ensaio;
- [ ] Ordem temporal pela linha do tempo: hipótese/plano registrados antes dos ensaios (CRI-D1, SIS-D2) e datas progressivas, não todas no fim (SIS-D6, T5);
- [ ] Consistência dos identificadores de versão entre cronologia ↔ `medicoes` ↔ `configuracao.json` (REP-D4) e a cadeia de fontes fechando: `cronologia.fonte` → `metodo.md#n`, `resultados.fonte` → `medicoes.csv#Snn` (REP-D6);
- [ ] Falha v1 → correção v2 registrada conta **a favor** de INC-D4 e REP-D3 (resultado negativo não desqualifica — T4);
- [ ] Início e fim do projeto pela cronologia min/max (SIS-D1, INC-D8);

#### Regras com LLM

- [ ] Um prompt por regra, com a definição e as fontes da regra, lendo só os fragmentos indicados no roteamento;
- [ ] Gate de citação: o trecho citado precisa existir literalmente no fragmento (checagem por substring); citação inventada é descartada;
- [ ] Cada evidência classificada como positiva / negativa / irrelevante (regra de nota em [[STS 2026 — Decisões do Modelo e do Back#Nota 0–100 (determinística)]]); regras de polaridade positiva (CRI-D6: método novo para tarefa comum conta) entram no prompt para evitar viés de rejeição;
- [ ] Texto sozinho (ex.: hipótese no §2) alcança no máximo PARCIAL; estado forte exige join com registro numérico por versão (intenção ≠ execução registrada);

#### Checagens cruzadas (armadilhas do pacote)

- [ ] Divergência entrevista × registro: extrair números e afirmações da transcrição e procurar o mesmo indicador em `resultados`/`medicoes` (mesma versão, ensaio e denominador). Registrar as duas versões: "a entrevista afirma X; o registro Y mostra Z; prevalece o registro". A divergência muda a justificativa, não a classe;
- [ ] Localizada ≠ comprovada: comparar o conteúdo esperado do `inventario_evidencias.csv` com o conteúdo real do arquivo;
- [ ] `MEMO-xx` na `revisao_tecnica.md` sem versão, saída ou registro → flag de elo ausente (PRJ27, PRJ33, PRJ35);
- [ ] Repetição de número em PDF (dossiê, registro técnico) não é confirmação independente; só o recompute valida;
- [ ] Unidades e denominadores incomparáveis (ex.: PRJ27 recuperação × resposta; PRJ34 500 pares, não 140 serviços);
- [ ] Rótulo × mecanismo: parâmetros do `configuracao.json` dentro da faixa do manual/runbook citado no §1 → sinal de configuração (NOV-D4, CRI-D5). Classificar pelo mecanismo, não pelo título ("inteligente", "nova arquitetura");
- [ ] Reteste ≠ validação (PRJ29), vazamento de informação futura (PRJ35, `volume_final`) e escopo excluído antes dos ensaios ≠ ressalva (PRJ23);
- [ ] Natureza das atividades (`natureza_informada_pela_equipe`) é autodeclaração: serve para INC-D9 (bug/manutenção), mas não discrimina classe sozinha;

#### Saída

- [ ] Cada evidência vira um nó `{regra_id, artefato#âncora, quote, polaridade, modo, natureza}` pronto para o grafo (tarefa 5);
- [ ] Regra sem evidência sai como "sem evidência" (fora da média), nunca como zero;
- [ ] Ligar com a pesquisa na web onde as regras se cruzam (ex.: NOV-D2 × NOV-W3, CRI-D5 × CRI-W2);
- [ ] Salvar no MongoDB com a versão do prompt/modelo e calibrar com os históricos PRJ01–20;


## 4. Módulo de Geração do Grafo
### Requisitos para tarefa concluída:

O grafo de evidências é a memória do sistema ([[2026-10-05-sts|reunião 2]]): todos os módulos escrevem nele, e o front, o parecer e o chatbot leem dele. Ele é montado a partir das evidências das seções 2 e 3 e acumula as notas por regra até o critério e a classe. Camadas 3 e 4 de [[organizacao-dados-por-criterio]]; nota 0–100 em [[STS 2026 — Decisões do Modelo e do Back#Nota 0–100 (determinística)]]; gabarito em [[historicos_classificados]].

#### Estrutura

- [ ] Nós: projeto · critério (5) · regra (`NOV/CRI/INC/SIS/REP-Wn/Dn` + T1–T8) · evidência · fonte (fragmento `arquivo#âncora` ou snapshot web) · query web · divergência · lacuna/elo ausente · decisão do analista;
- [ ] Arestas: evidência **sustenta** / **contraria** regra · evidência **cita** fonte · query **retornou** fonte · regra **compõe** critério · critério **compõe** classe · divergência **liga** depoimento × registro (com qual **prevalece**) · analista **decidiu** classe;
- [ ] Propriedades obrigatórias da evidência: `regra_id`, `quote`, `polaridade`, `modo` (REGRA / LLM / WEB), `natureza` (registro primário, síntese, depoimento, derivado), versão do modelo/prompt e timestamp;

#### Construção

- [ ] Script idempotente para adicionar nós: ID determinístico (hash de regra + fonte + trecho), para reanálise não duplicar evidência;
- [ ] Reanálise gera nova versão do grafo, nunca sobrescreve; guardar o diff entre versões (o que entrou, saiu, mudou de polaridade) — dossiê versionado com autor e data (SIS-D10);
- [ ] Salvar no MongoDB em duas coleções (`nodes`, `edges`), percorridas com `$graphLookup`; não precisa de banco de grafo;

#### Pontuação (do nó de evidência até o critério)

- [ ] Nota da regra = positivas / (positivas + negativas); a mesma fonte conta uma vez por regra (deduplicar por DOI, família de patente e fragmento);
- [ ] Regra sem evidência = "sem evidência", fora da média; N/A e parciais saem com o motivo; NOV-W1, W2 e W8 só informativas;
- [ ] Depoimento tem peso zero: entra no grafo como contexto e divergência, nunca como evidência que pontua;
- [ ] Nota do critério = média das regras, mostrada ao analista como indicador — **a classe não sai da média** (ver abaixo);

#### Estado por critério (vocabulário do gabarito)

- [ ] Usar o vocabulário exato de cada critério em `historicos_classificados.csv`:

| Critério | Positivo | Negativo (rotina) | Indeterminado |
|---|---|---|---|
| Novidade | DEMONSTRADA NO RECORTE | NÃO DEMONSTRADA | INDETERMINADA |
| Criatividade técnica | DEMONSTRADA NO RECORTE | NÃO DEMONSTRADA | INDETERMINADA |
| Incerteza tecnológica | INVESTIGADA | NÃO CARACTERIZADA | ALEGADA, NÃO VERIFICÁVEL |
| Sistematicidade | DOCUMENTADA | DOCUMENTADA COMO ACEITE | PARCIAL |
| Transferência/reprodução | DOCUMENTADA NO ESCOPO · DOCUMENTADA COM LIMITE | DOCUMENTADA PARA A CONFIGURAÇÃO | INSUFICIENTE PARA O NÚCLEO ALEGADO |

- [ ] Gates que forçam o estado, independente da nota: um documento anterior com cobertura total (NOV-W3) ou ajuste dentro da faixa do manual (NOV-D4, CRI-D5) → negativo; núcleo só com MEMO/sem registro → indeterminado; estado positivo exige join com registro numérico por versão;
- [ ] Limitação **dentro** da pretensão original → "DOCUMENTADA COM LIMITE"; limite excluído antes dos ensaios não gera ressalva (PRJ23);

#### Classe (regras de decisão)

- [ ] Derivar a classe do vetor de estados, como no gabarito PRJ01–20:
  - todos positivos + transferência **NO ESCOPO** → Elegível;
  - todos positivos + transferência **COM LIMITE** → Com ressalvas;
  - negativo nos critérios de novidade/criatividade/incerteza (sistematicidade "como aceite") → Não elegível;
  - indeterminado no núcleo → Evidência insuficiente;
- [ ] Vetor fora desses padrões (ex.: novidade positiva e incerteza negativa) → sem classe automática, flag de inconsistência para o analista (Fleming 2001: novidade forte sem incerteza é sinal de descrição inconsistente);
- [ ] Saída obrigatória por classe: Com ressalvas → recorte sustentado, limitação e evidência necessária; Evidência insuficiente → elo ausente e evidências a solicitar;

#### Analista e rastreabilidade

- [ ] O sistema sugere estado e classe; o analista confirma ou altera com justificativa. A decisão vira nó com quem e quando (T7) e nunca apaga a sugestão original;
- [ ] Toda afirmação do parecer precisa de caminho no grafo até uma fonte; afirmação sem caminho não entra;

#### Consumo

- [ ] Entregar ao módulo de parecer (seção 6) os dados no schema do gabarito (27 colunas: classificação, justificativa, limite, fontes decisivas, divergência de depoimento e critério/estado/justificativa/fonte × 5), mais o grafo para o relatório final;
- [ ] Visualização no front: projeto → critérios → regras → evidências, cor por polaridade, clique abre o trecho citado;
- [ ] API de consulta para o chatbot (tarefa 6): responde só com nós do grafo e cita o ID;
- [ ] Calibração com PRJ01–20: classe e estado por critério comparados ao gabarito (matriz de confusão), antes de rodar PRJ21–40;


## 5. Orquestrador da Análise
### Requisitos para tarefa concluída:

Define quem chama quem, em que ordem, e como o front acompanha. Cobre o caminho ponta a ponta exigido na demo (projeto entra → documento sai) e dois diferenciais citados no [[GUIA_DO_PARTICIPANTE]]: **processamento em lote com acompanhamento do andamento** e **reanálise após inclusão de evidências**. Fluxo de execução na Parte 2 de [[organizacao-dados-por-criterio]].

#### Pipeline

- [ ] Ordem fixa das etapas: extração (1) → regras determinísticas (3, modo REGRA: recompute, linha do tempo, versões) → pesquisa na web (2) e regras com LLM (3) em paralelo → grafo, estados e classe (4) → parecer (6). O recompute vem antes de qualquer LLM, porque é contra os números recalculados que as alegações são testadas;
- [ ] Cada etapa lê e escreve só pelo JSON canônico e pelo grafo — nenhum módulo chama outro diretamente;
- [ ] Execução assíncrona: o upload devolve um `analise_id` na hora e o processamento roda em background (fila de jobs);

#### Status e acompanhamento

- [ ] Status por etapa e por projeto (`pendente` · `rodando` · `concluída` · `falhou` · `não executada`), com início, fim e duração;
- [ ] Endpoint de status para o front (polling ou SSE/WebSocket) mostrar o andamento em tempo real;
- [ ] Registrar o tempo total por projeto — é o número que responde à pergunta 3 da banca ("reduz o tempo de análise?");

#### Falha parcial

- [ ] Falha de uma etapa não derruba a análise: se a web cair, as regras W ficam "não executadas" (nunca zero) e o resto segue; o parecer diz o que não rodou;
- [ ] Retry com backoff para chamadas externas (APIs de busca, LLM em nuvem) e timeout por etapa;
- [ ] Arquivo não reconhecido não trava o pipeline: a análise roda e o front mostra "pendente de validação" (seção 1);

#### Lote

- [ ] Aceitar vários projetos de uma vez (ex.: PRJ21–40 ou o pacote inteiro), com fila e limite de concorrência (para não estourar rate limit de API nem a GPU do Ollama);
- [ ] Painel do lote: quantos concluídos, rodando, com falha, e a classe sugerida de cada um assim que sai;

#### Reanálise

- [ ] Incluir ou substituir um arquivo dispara reanálise **incremental**: refazer só a extração do arquivo novo e as regras cujo roteamento aponta para ele (a tabela regra → artefato da seção 3 diz quais);
- [ ] Correção do analista (tipo de arquivo, seção, achado irrelevante, URL manual) também dispara reanálise das regras afetadas;
- [ ] Toda reanálise gera nova versão do grafo e do parecer, com o diff para a anterior (o que mudou e por quê); a decisão anterior do analista é preservada e sinalizada como "a revisar" se a classe sugerida mudar;

#### Reprodutibilidade da execução

- [ ] Registrar por análise: hash dos arquivos (manifest), versão de cada módulo, modelo e prompt usados, versão do catálogo de regras, cache das buscas web;
- [ ] Reexecutar uma análise antiga com as mesmas versões dá o mesmo resultado (temperature 0 + cache);

## 6. Gerador de Parecer
### Requisitos para tarefa concluída:

Produz o documento final, que responde à pergunta 2 da banca: *"o documento final é claro e defensável numa fiscalização?"*. O conteúdo segue a "Entrega esperada" do [[GUIA_DO_PARTICIPANTE]] e o schema de `historicos_classificados.csv`; os requisitos de registro vêm de [[Dossiê e Rastreabilidade]]. O parecer só monta o que está no grafo (seção 4) — não decide nada.

#### Conteúdo (entrega esperada do guia)

- [ ] Classificação recomendada (Elegível · Com ressalvas · Não elegível · Evidência insuficiente) e justificativa da conclusão;
- [ ] Avaliação dos cinco critérios: estado (vocabulário do gabarito), justificativa e fonte por critério;
- [ ] Com ressalvas → recorte sustentado pelas evidências, limitação específica e evidência necessária para resolver a ressalva;
- [ ] Evidência insuficiente → elo ausente e evidências adicionais a solicitar;
- [ ] Evidências usadas, por ID (`PRJ21-S02`, `metodo.md#2`, snapshot web com data);
- [ ] Evidências contrárias ou contraditórias, incluindo divergências depoimento × documento no formato do guia: "a entrevista afirma X; o registro Y mostra Z; prevalece o registro, por ser primário e identificado por versão";
- [ ] Lacunas identificadas, incluindo regras N/A ou não executadas, com o motivo;
- [ ] Registro de rastreabilidade: regra ou critério aplicado, informação do projeto que sustenta a decisão, e quem decidiu e quando (a decisão final é do analista);

#### Defensabilidade

- [ ] Toda frase do parecer tem caminho no grafo até uma fonte; frase sem fonte não entra (gate de citação, como nas seções 1 e 3);
- [ ] Separar visualmente a sugestão do sistema e a decisão do analista; se o analista alterou, mostrar as duas e a justificativa;
- [ ] Anexo da busca web: bases, strings, filtros, datas, nº de resultados e selecionados (log PRISMA-S, NOV-W8), para quem fiscalizar refazer a busca;
- [ ] Citar a regra normativa por trás de cada critério (Frascati §, Guia MCTI, FAQ) a partir das notas de critérios, para o leitor ver de onde vem a exigência;

#### Linguagem e formato

- [ ] Texto para quem não conhece a norma a fundo (pergunta 4 da banca): primeiro um resumo de uma página (classe + por quê em 3–5 linhas + o que falta), depois o detalhe por critério;
- [ ] LLM só redige a partir dos campos do grafo (textos curtos, sem acrescentar fato); números sempre copiados do registro, nunca reescritos pela LLM;
- [ ] Exportar em PDF e DOCX; exportar também CSV/JSON no schema do gabarito (27 colunas) para comparar com PRJ01–20 e para processamento em lote;

#### Pedido de complementação

- [ ] Gerar, a partir dos elos ausentes e lacunas, uma lista do que pedir à equipe do projeto (ex.: PRJ27 → "vínculo pergunta → trecho → resposta → fonte, com versão do gerador"), pronta para o analista enviar;

#### Versionamento

- [ ] Cada parecer tem versão, data, hash do conteúdo e referência à versão do grafo e da análise que o gerou; reanálise gera nova versão, nunca sobrescreve;
- [ ] Guardar no MongoDB e permitir baixar qualquer versão anterior — o governo pode perguntar anos depois (SIS-D10);

## 7. Chatbot
### Requisitos para tarefa concluída:

O chat de "tira dúvidas" da [[2026-10-02-sts|reunião 1]] (tarefa 6 de [[Tasks]]). Ajuda a responder à pergunta 4 da banca: *"alguém sem conhecimento profundo das normas consegue usar?"*. O guia do desafio avisa que "não adianta criar mais um lugar onde ler as normas": o chat é **meio** para entender a análise, não o produto — ver [[RAG sobre Documentos Normativos]].

#### Duas bases de resposta

- [ ] **Grafo do projeto** (seção 4): perguntas sobre a análise — "por que o PRJ21 é não elegível?", "qual evidência sustenta a incerteza?", "onde a entrevista diverge do registro?";
- [ ] **Base normativa**: perguntas sobre a regra — "o que é incerteza tecnológica?", "configurar produto pronto conta como P&D?". RAG sobre os PDFs de `docs/` (Lei 11.196, Decreto 5.798, Portaria 9.563/2025, Frascati 2015/2002, Guia MCTI 2020, FAQ, Guia ANPEI 2017), fatiados por artigo/§ com metadados (norma, §, página, versão), busca híbrida BM25 + vetor (`bge-m3`) e reranker;
- [ ] Roteamento da pergunta: sobre o projeto → grafo; sobre a norma → base normativa; misturada ("por que a NOV-W3 derrubou a novidade?") → as duas, citando nó do grafo e trecho da norma;

#### Fundamentação

- [ ] Toda resposta cita a fonte: ID do nó/evidência do grafo ou norma + §/página; resposta sem fonte recuperada → "não encontrei base para responder", nunca resposta de memória do modelo (T7);
- [ ] Gate de citação: o trecho citado precisa existir literalmente na fonte recuperada (mesma checagem das seções 1 e 3);
- [ ] Clique na citação abre o trecho no front (fragmento do projeto, página do PDF normativo ou snapshot web);
- [ ] Números sempre copiados do registro, nunca recalculados ou arredondados pelo modelo;

#### Limites

- [ ] O chat **explica, não decide**: não muda estado, classe nem parecer. Pedido do tipo "muda para elegível" → orienta o analista a usar a revisão com justificativa;
- [ ] Ao explicar uma classe, mostrar as evidências contrárias e as divergências também, não só as que sustentam a conclusão;
- [ ] Conteúdo de documentos e páginas web tratado como dado, nunca como instrução (defesa contra prompt injection);

#### Ações úteis para o analista

- [ ] Explicar uma regra pelo ID (ex.: "o que é CRI-W2?"), lendo do catálogo de regras (seção 8);
- [ ] Sugerir a evidência que falta para resolver uma ressalva ou um elo ausente, a partir do pedido de complementação (seção 6);
- [ ] Comparar com os históricos PRJ01–20 só como **exemplo de raciocínio**, nunca como base de classificação ("parece com o PRJ05") — o [[GUIA_DO_PARTICIPANTE]] proíbe classificar por semelhança;

#### Rastreabilidade

- [ ] Salvar a conversa no MongoDB ligada à análise e à versão do grafo consultada (pergunta, fontes recuperadas, resposta, modelo, timestamp);
- [ ] Uma resposta do chat pode ser anexada ao parecer como nota do analista, com a fonte junto;

## 8. Catálogo de Regras
### Requisitos para tarefa concluída:

As 66 regras (58 específicas + T1–T8) viram **dado versionado**, não texto espalhado no código e nos prompts. Os módulos de web (2), documento (3), grafo (4), parecer (6) e chatbot (7) leem do mesmo lugar. Fonte do conteúdo: [[Regras de Validação dos Critérios de Frascati]] e as 5 notas de critérios; mapeamento dado → regra na Parte 3 de [[organizacao-dados-por-criterio]].

#### Schema de cada regra

- [ ] `id` (`NOV-W3`, `SIS-D2`, `T6`…), critério, bloco (web / documento / transversal);
- [ ] O que verificar e a evidência que sustenta (texto da nota de critério);
- [ ] Fontes normativas com § ou página (Frascati, Guia MCTI, FAQ, fiscos estrangeiros) e a hierarquia da fonte (norma BR > orientação MCTI > fisco estrangeiro > analogia de patente > artigo);
- [ ] Roteamento: artefatos e seções do pacote que a regra lê (ex.: NOV-D1 → `metodo.md#2`) ou família de query web (ex.: CRI-W2 → documentação oficial/tutorial);
- [ ] Modo (REGRA / LLM / WEB / combinações) e, se REGRA, a função que a implementa;
- [ ] Polaridade padrão e casos especiais (ex.: CRI-D6 e T4 contam a favor; falha v1 → v2 é positiva para INC-D4 e REP-D3);
- [ ] Papel na pontuação: entra na média, informativa (NOV-W1, W2, W8) ou gate que força estado (NOV-W3 cobertura total, NOV-D4, CRI-D5);
- [ ] Status no pacote: aplicável · parcial · N/A, com o motivo (NOV-D7, SIS-D4, SIS-D8, SIS-D10, T2 são N/A; SIS-D3, SIS-D9, REP-D4 parciais);
- [ ] Prompt da regra (para as de LLM) e explicação em linguagem simples (para o parecer e o chatbot);

#### Formato e versionamento

- [ ] Um arquivo YAML/JSON no repositório (revisável em PR), carregado no MongoDB na subida do back;
- [ ] Versão semântica do catálogo; toda análise e todo parecer registram a versão usada (seção 5), para saber com qual regra um projeto foi avaliado anos depois;
- [ ] Mudança de regra não altera análises antigas; reanalisar com o catálogo novo é uma ação explícita e gera nova versão;

#### Validação do catálogo

- [ ] Teste automático: toda regra das notas de critérios está no catálogo (as 66 da auditoria de 07/10), sem ID duplicado ou órfão;
- [ ] Toda regra de modo REGRA aponta para uma função existente; toda regra LLM tem prompt; todo artefato do roteamento existe no schema do JSON canônico;
- [ ] Endpoint de leitura (`GET /regras`, `GET /regras/{id}`) para o front mostrar a regra ao clicar num nó do grafo;
