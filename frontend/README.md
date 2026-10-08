# Front-end: Lei do Bem · Apoio à Decisão

Front-end do Hackathon STS 2026 (desafio BNB). O visual de alta fidelidade vem do Figma
do designer (identidade do BNB: Heebo, vinho `#A6193C`) e está sendo aplicado tela a
tela. A árvore de evidências segue o Figma; projetos, upload, documento de decisão, login
e chatbot foram derivados do mesmo design system (não há tela deles no Figma).

> A ferramenta **apoia** a decisão, não decide. As notas são **força da evidência**
> (0–100), nunca "probabilidade de aprovação".

## Rodando

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # Vitest (funções puras: árvore, grafo)
npm run lint       # oxlint
npm run build      # tsc + vite build
npm run test:e2e   # Playwright: jornadas de usuário no navegador (sobe o Vite na porta 5180)
```

Na primeira vez, instale o navegador dos testes: `npx playwright install chromium`.
`npm run test:e2e:ui` abre o modo visual (passo a passo, com prints) e
`npm run test:e2e:report` mostra o relatório da última execução.

### Testes ponta a ponta (`e2e/`)

- `journeys.spec.ts`: jornadas como uma pessoa faria à mão, usando só o que aparece na tela
  (primeira análise até o PDF, contestação e reanálise, upload, triagem da fila, mapa
  geral com o mouse, só teclado e celular).
- `login`, `projects`, `analysis`, `decision`: verificações pontuais de cada tela.
- Todo teste começa com dados de demonstração limpos (contexto novo do navegador) e falha
  se a página registrar erro no console.

Stack: Vite 8, React 19 (React Compiler ligado), TypeScript, Tailwind v4,
React Router 7 (modo declarativo), TanStack Query, React Flow + dagre,
react-resizable-panels, react-dropzone, react-to-print, lucide-react.

## Telas

| Rota | Tela |
|---|---|
| `/login` | Login e Cadastro do **Lastro** (mock: analistas de demonstração ou conta criada na hora, qualquer senha) |
| `/projetos?q=&status=&banda=&decisao=&de=&ate=&ordem=&pagina=&novo=1` | Meus projetos: cards por situação (também filtram), filtros (critério mais fraco, decisão, período, ordem), busca, situação de cada projeto e "Reenviar arquivo"; "Novo projeto" (`novo=1` abre o upload) |
| `/projetos/:id/analise?metodo=<método>&no=<nó>` | Árvore de evidências: detalhamento (critérios em acordeão) + grafo Critério → Regra → Evidência + decisão do analista por regra |
| `/projetos/:id/decisao?metodo=<método>` | Documento de decisão (todos os métodos) com as notas do analista por regra e a triagem de evidências, formulário da decisão final, trilha e PDF |

Nas telas de análise e decisão há um **assistente** (botão no canto inferior direito)
que explica notas, evidências e rastreabilidade. Ele entende o item selecionado, números
(`3.1.1`), códigos (`PROJ-13`) e nomes de critério, e cada resposta traz links para os nós.

O nó selecionado fica na URL (`?no=crit-uncertainty.rule-proj-13.ev-1`): voltar/avançar
funciona e dá para compartilhar um link que aponta para uma evidência.

## Onde mexer

```
src/
  domain/      tipos (contrato provisório), faixas de nota (score.ts), árvore numerada (tree.ts)
  mocks/       projetos e análises FICTÍCIOS
  services/    api.ts (camada única de dados, inclusive askAssistant) + queries.ts
  features/
    projects/  tabela, modal de novo projeto, dropzone
    analysis/  useAnalysisExplorer (seleção, visão do grafo), detail/ (painel), graph/
    decision/  relatório imprimível, formulário, trilha
    assistant/ chatbot: provider (conversa por projeto) e widget
  components/  layout (AppLayout, ProjectHeader), ícones do design e UI compartilhada (Tag, ReferenceLink, estados)
  pages/       uma pasta por rota
  index.css    tokens do tema (@theme) e CSS de impressão
```

- **Assistente real:** trocar o corpo de `askAssistant` em `src/services/api.ts`. O
  contrato está em `src/domain/assistant.ts`; a versão mock (regras, sem IA) fica em
  `src/mocks/assistantEngine.ts`.
- **Trocar mocks pela API real:** só `src/services/api.ts`. As telas consomem apenas
  essas funções. Os tipos esperados estão em `src/domain/types.ts`.
- **Visual do designer:** cores, sombras e fonte são tokens em `src/index.css`, com os nomes
  das variáveis do Figma comentados. A "Etiqueta" do design é `components/ui/Tag.tsx`; os
  botões são `.btn-primary`, `.btn-secondary` e `.btn-chip`. Os cards do grafo ficam em
  `features/analysis/graph/GraphNodes.tsx`.
- **Rótulos qualitativos** ("Sustentado", "Parcialmente", "Contraditório"...): vêm da nota e
  das evidências em `src/domain/qualitative.ts`. Cada critério usa a palavra do design
  ("Demonstrada no recorte", "Investigada", "Documentada", "Com limite"…). O número 0–100
  continua no detalhamento.
- **Decisão final:** Elegível / Com ressalvas / Não elegível (`src/domain/labels.ts`).
- **Upload (simulado):** tipo de documento reconhecido pelo nome (`src/domain/documents.ts`),
  progresso por arquivo, pastas inteiras, PDF/DOCX/TXT/MD/CSV/XLSX/JSON e o consentimento
  para buscar trabalhos similares na web. Nada sai do navegador até existir o back-end.
- **Faixas de nota:** `src/domain/score.ts` (`scoreBand()`); o resto da UI segue.

## Funcionalidades de apoio ao analista

- **Composição da nota:** cada critério e regra mostra, em gráfico, como a nota foi formada
  (ponto de partida, contribuição de cada evidência/regra e ajustes). É **mockada**
  (`src/mocks/scoreExplanations.ts`) até o time definir o cálculo; o contrato é
  `scoreExplanation` em `src/domain/types.ts`.
- **Contestação e reanálise:** "Questionar" no detalhe de qualquer nó abre o assistente em
  modo debate. O modelo mostra a base, simula o efeito (ex.: inverter a polaridade de uma
  evidência) e o analista registra a contestação (status **aberta**). Ao pedir a
  **reanálise** (no chat ou no detalhe do nó), ela vira **resolvida**: *acatada* (a análise
  é ajustada, e os itens aparecem como "revisado") ou *leitura mantida*. No mock, o modelo
  acata quando o argumento cita uma fonte verificável (página, arquivo, tabela, anexo)
  (`src/mocks/reanalysis.ts`). Tudo entra na trilha de decisão.
- **Vários métodos:** cada projeto tem uma análise por método (`src/domain/frameworks.ts`).
  Hoje: Manual de Frascati e Formulário MCTI. Para incluir outro, adicione-o ali e nos mocks.

## Comportamentos já decididos

- **Grafo por critério + mapa geral.** Por padrão o grafo mostra o critério selecionado
  com todas as regras e evidências (como no Figma). "Mapa geral" mostra os 5 critérios:
  na primeira vez tudo aparece expandido e depois recolhe para os critérios; clicar num
  critério ou regra expande, clicar de novo recolhe.
- **Decisão do analista por regra.** Cada regra recebe a nota do analista com
  justificativa obrigatória; evidências podem ser confirmadas ou descartadas (descartar pede
  o motivo). Um critério conta como "decidido" quando todas as regras têm nota. A decisão
  final do projeto continua no documento de decisão. Tudo é só acrescentado.
- **Decisão nunca é sobrescrita.** Cada registro entra na trilha (quem, quando, com base
  em qual análise); a mais recente é a "vigente".
- **Cada analista vê os próprios projetos.** Decisões e contestações são assinadas pelo
  usuário logado.
- **Mock persistente.** O banco mockado fica no `localStorage`, então uma demo sobrevive
  ao F5. Para voltar aos exemplos: `resetMockData()` no console (modo dev). Ao mudar
  `src/mocks`, troque a versão de `STORAGE_KEY` em `api.ts`.
