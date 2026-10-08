# Front-end: Lei do Bem · Apoio à Decisão

Esqueleto do front-end do Hackathon STS 2026 (desafio BNB). O visual é **provisório**:
a alta fidelidade do designer entra trocando os tokens do tema e os componentes de
apresentação, sem mexer na lógica.

> A ferramenta **apoia** a decisão, não decide. As notas são **força da evidência**
> (0–100), nunca "probabilidade de aprovação".

## Rodando

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # Vitest (funções puras: árvore, grafo)
npm run lint       # oxlint
npm run build      # tsc + vite build
```

Stack: Vite 8, React 19 (React Compiler ligado), TypeScript, Tailwind v4,
React Router 7 (modo declarativo), TanStack Query, React Flow + dagre,
react-resizable-panels, react-dropzone, react-to-print, lucide-react.

## Telas

| Rota | Tela |
|---|---|
| `/projetos` | Lista de projetos + "Novo projeto" (arquivos e/ou texto livre) |
| `/projetos/:id/analise?no=<nó>` | Árvore + detalhe + grafo Critério → Regra → Evidência |
| `/projetos/:id/decisao` | Documento de decisão, formulário do analista, trilha e PDF |

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
    analysis/  useAnalysisExplorer (seleção + expansão), tree/, detail/, graph/
    decision/  relatório imprimível, formulário, trilha
    assistant/ chatbot: provider (conversa por projeto) e widget
  components/  layout e UI compartilhada (ScoreBadge, PolarityTag, ReferenceLink, estados)
  pages/       uma pasta por rota
  index.css    tokens do tema (@theme) e CSS de impressão
```

- **Assistente real:** trocar o corpo de `askAssistant` em `src/services/api.ts`. O
  contrato está em `src/domain/assistant.ts`; a versão mock (regras, sem IA) fica em
  `src/mocks/assistantEngine.ts`.
- **Trocar mocks pela API real:** só `src/services/api.ts`. As telas consomem apenas
  essas funções. Os tipos esperados estão em `src/domain/types.ts`.
- **Visual do designer:** cores e fontes são tokens em `src/index.css` (`--color-score-strong`,
  `--color-evidence-negative`, ...). Os cards do grafo ficam em `features/analysis/graph/GraphNodes.tsx`.
- **Faixas de nota:** `src/domain/score.ts` (`scoreBand()`); o resto da UI segue.

## Comportamentos já decididos

- **Grafo mostra os 5 critérios.** Ao entrar na tela, tudo aparece expandido e depois
  recolhe para só os critérios. Clicar num critério ou regra expande; clicar de novo recolhe.
- **Decisão nunca é sobrescrita.** Cada registro entra na trilha (quem, quando, com base
  em qual análise); a mais recente é a "vigente".
- **Mock persistente.** O banco mockado fica no `localStorage`, então uma demo sobrevive
  ao F5. Para voltar aos exemplos: `resetMockData()` no console (modo dev). Ao mudar
  `src/mocks`, troque a versão de `STORAGE_KEY` em `api.ts`.
