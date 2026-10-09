# Pendências

Pontos deixados para depois. Separados em dois grupos:

- **Essenciais:** o que falta para o app funcionar de verdade (ou para a demo ficar
  correta) dentro do hackathon.
- **Escopo maior:** mudanças para o caso de o projeto continuar depois do hackathon.

---

## Essenciais (app funcionando / demo)

### Integração com o back-end

- [ ] Trocar os mocks pela API real em `src/services/api.ts` (projetos, análises,
      decisões, contestações). As telas só usam essas funções.
- [ ] Confirmar com o back-end a **escala da nota** (hoje 0–100, faixas em
      `src/domain/score.ts`) e os **formatos de upload** aceitos (hoje PDF, DOCX, TXT, MD, CSV, XLSX e JSON).
- [ ] Upload real dos arquivos (hoje só os metadados são guardados e o progresso é
      simulado em `src/features/projects/uploadQueue.ts`).
- [ ] **Reconhecimento do tipo de documento** pelo conteúdo (hoje só pelo nome, em
      `src/domain/documents.ts`) e leitura de CSV, XLSX, JSON e MD.
- [ ] **Busca de trabalhos similares na web** (Google Scholar e arXiv) com aprovação dos
      termos pelo analista: hoje só o consentimento é guardado (`Project.webSearch`).
- [ ] **Reenvio de arquivo ilegível** (`resendDocument`) e o nome do arquivo com erro
      (`Project.readError`) vindos do back-end.
- [ ] **Data de corte** do recorte analisado (`Project.cutoffDate`) e o progresso do
      processamento (`processingProgress`) vindos do back-end.
- [ ] **Cálculo da nota:** substituir a composição mockada (`src/mocks/scoreExplanations.ts`)
      pela explicação real do back-end, no formato `scoreExplanation`.
- [ ] **Chatbot:** trocar as respostas mockadas (`askAssistant` em `src/services/api.ts`)
      pela integração com o ai-microservice. Manter as regras: nunca dar veredito,
      falar em "força da evidência" e sempre citar a fonte.
- [ ] **Reanálise de contestações:** trocar o mock (`src/mocks/reanalysis.ts`) pela
      reanálise real do modelo, mantendo o formato `ContestationResolution`.

### Conteúdo e terminologia

- [ ] **Conferir as referências normativas dos mocks.** Algumas seções foram escritas
      como placeholder e não foram verificadas: "Guia Prático da Lei do Bem (MCTI) §7
      (exclusões)", "Manual de Frascati §2.49" e "§2.68". Também confirmar se as URLs do
      Planalto (Lei 11.196/2005 e Decreto 5.798/2006) abrem o texto certo.
      Arquivos: `src/mocks/references.ts`, `src/mocks/analysis-*.ts`.
- [ ] **Nomes das classificações PB / PA / DE.** Hoje: "Pesquisa básica", "Pesquisa
      aplicada", "Desenvolvimento experimental" (Frascati + Decreto 5.798/2006, art. 2º).
      O decreto fala em "pesquisa básica **dirigida**". Os nomes devem mudar; ajustar em
      `src/domain/labels.ts`.
- [ ] Revisar o conteúdo da árvore mockada do **Formulário MCTI**
      (`src/mocks/analysis-soil-sensor-mcti.ts`).

### Visual e técnico

- [x] Visual de alta fidelidade aplicado em todas as telas, todas do Figma: cabeçalho,
      árvore de evidências, projetos, upload, login, assistente ("IA Assistente", com
      animação de abrir/fechar) e documento de decisão (um método por vez, pendências,
      sanfona, 4 classificações).
- [ ] Busca da lista perdeu letras uma vez no e2e (campo ficou com "s" em vez de "sensor"),
      só com os testes rodando em dobro e em paralelo (`--repeat-each=2`). Não reproduzido
      em uso normal; investigar se o campo é recriado durante o carregamento da lista.
- [x] Fontes: Heebo carregada do Google Fonts (o documento de decisão também usa Heebo).
- [ ] Bundle passa de 500 kB por causa do React Flow: carregar as telas sob demanda
      (`React.lazy` nas rotas de análise e decisão).

### Fora do front-end (avisar o time)

- [ ] O commit inicial do microserviço de IA (hoje em `backend/src/ai_microservice`)
      incluiu arquivos `__pycache__/*.pyc`; ajustar o `.gitignore` de lá.

---

## Escopo maior (se o projeto continuar)

- [ ] **Login e cadastro reais** (hoje: mock com sessão no `localStorage`, `src/features/auth`;
      o cadastro cria a conta no banco mockado e aceita qualquer senha, sem guardá-la).
- [ ] **Permissões:** hoje um analista consegue abrir o projeto de outro por link direto
      (só a lista é individual). Definir regras de acesso e uma **visão de coordenação**
      com os projetos de toda a equipe.
- [ ] **Trilha em banco de dados** (hoje `localStorage`), mantendo o comportamento de só
      acrescentar registros (decisões, contestações e reanálises nunca são apagadas).
- [ ] **Versões da análise:** hoje uma contestação acatada ajusta a análise "por cima"
      (lista de ajustes). Com back-end, cada reanálise poderia gerar uma nova versão
      da análise, e a decisão apontaria para a versão exata que o analista viu.
- [ ] **Outros métodos de árvore** além de Frascati e Formulário MCTI (ex.: Manual de Oslo):
      basta incluir em `src/domain/frameworks.ts` e no back-end.
- [ ] **Dados de demonstração:** os ~400 projetos gerados reaproveitam os textos do
      projeto-exemplo do sensor (só as notas variam). Servem para teste de escala e para a
      banca; num produto real saem de cena.
- [ ] **Exclusões (EXC-xx)** ficam como regras dentro dos critérios (decidido). Revisitar
      se o back-end mandar um grupo próprio.
