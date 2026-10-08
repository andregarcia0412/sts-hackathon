# AGENTS.md: front-end

Guia para agentes de IA (e pessoas) que forem mexer nesta pasta. Para a visão geral do
produto e das telas, leia o `README.md`. O que ficou para depois está no `PENDENCIAS.md`.

## O produto em 3 regras

Ferramenta de apoio à análise preliminar de enquadramento na Lei do Bem (Lei 11.196/2005).
Toda mudança precisa respeitar:

1. **A ferramenta apoia, não decide.** Nunca mostrar "aprovado"/"reprovado" como veredito
   automático, nem no chatbot. Quem decide é o analista.
2. **A nota é "força da evidência" (0–100)**, nunca "probabilidade de aprovação".
3. **Rastreabilidade em tudo.** Toda nota leva, em 1 ou 2 cliques, à regra, ao trecho do
   documento e à referência normativa. Decisões, contestações e reanálises são **só
   acrescentadas**, nunca editadas ou apagadas.

Todos os dados de exemplo são **fictícios** e precisam continuar identificados assim.

## Comandos

```bash
npm install
npm run dev        # Vite em http://localhost:5173
npm test           # Vitest (vitest run)
npm run lint       # oxlint
npm run build      # tsc -b && vite build
```

Antes de considerar uma tarefa pronta: `npm test`, `npm run lint` sem avisos, `npm run build`
e conferir a tela no navegador (login de demonstração: qualquer analista, qualquer senha).

## Stack

Vite 8, React 19 com **React Compiler** (o `useMemo` manual quase nunca é necessário),
TypeScript 6 (`verbatimModuleSyntax` → use `import type`; `erasableSyntaxOnly` → sem `enum`),
Tailwind v4 (tokens em `src/index.css` via `@theme`), React Router 7 **declarativo**
(`<BrowserRouter>`/`<Routes>`), TanStack Query, React Flow (`@xyflow/react`) + `@dagrejs/dagre`,
react-resizable-panels v4 (`Group`/`Panel`/`Separator`), react-dropzone, react-to-print,
lucide-react. Gerenciador: **npm**. Não troque nem adicione dependências sem combinar com o time.

## Convenções

- Identificadores e comentários em **inglês**; textos da interface em **pt-BR**.
- Componentes como `export const Nome = () => …` (exports nomeados). Imports com o alias `@/`.
- Arquivos `.tsx` de componente **só exportam componentes** (regra do oxlint para Fast
  Refresh). Constantes, estilos e helpers vão para um `.ts` ao lado (ex.: `scoreStyles.ts`).
- Classes do Tailwind sempre **estáticas** (mapas `Record<…, string>`), nunca montadas por
  interpolação, para o Tailwind encontrá-las.
- Cor nunca é a única informação: faixa de nota e polaridade sempre com ícone ou rótulo.
- Efeitos que reagem a um "evento" (ex.: só quando a seleção muda) usam `useEffectEvent`,
  em vez de desligar a regra `exhaustive-deps`.
- Commits pequenos e com escopo: `feat(frontend): …`, `fix(frontend): …`, `docs(frontend): …`.

## Arquitetura

```
src/
  domain/        tipos (contrato provisório com o back-end) e funções puras
                 types.ts · tree.ts · score.ts · frameworks.ts · contestations.ts · assistant.ts
  mocks/         dados FICTÍCIOS e motores mockados (chatbot, debate, reanálise, explicação
                 da nota, ~400 projetos gerados, filtros da lista)
  services/      api.ts = ÚNICA camada de dados · queries.ts = hooks do TanStack Query
  features/      projects · analysis (tree, detail, graph) · decision · assistant · auth
  components/    layout e UI compartilhada (ScoreBadge, ReviewTag, ScoreBreakdown…)
  pages/         uma pasta por rota
  routes/        AppRouter.tsx e paths.ts (montagem de URLs)
```

- As telas **só** falam com `src/services/api.ts`. Integrar o back-end é trocar o corpo
  dessas funções, mantendo os tipos de `src/domain/types.ts`.
- A lógica de negócio fica em funções puras (`domain/`, `mocks/`) com teste ao lado
  (`*.test.ts`). Componentes só apresentam.

## Regras do domínio que o código assume

- **IDs de nó são caminhos**: `crit-uncertainty.rule-proj-13.ev-1`. São únicos dentro de uma
  análise e aparecem na URL. A numeração 1 / 1.1 / 1.1.1 vem de `indexAnalysis()` e é a
  mesma na árvore, no grafo e no documento de decisão.
- **Estado na URL**: `?metodo=` (árvore/método) e `?no=` (nó selecionado) na análise; os
  filtros da lista de projetos também. É a fonte de verdade da seleção.
- **Um projeto tem uma análise por método** (`FRAMEWORKS` em `domain/frameworks.ts`). Para
  incluir um método, adicione-o ali e nos mocks/back-end.
- **Faixas de nota** só em `scoreBand()` (`domain/score.ts`).
- **Contestação**: `open` → reanálise → `resolved` (`accepted` ajusta a análise via
  `applyAdjustments`; `maintained` não muda nada). As análises devolvidas pela API já vêm
  com os ajustes aplicados.
- O grafo mostra **todos os critérios**. Ao abrir a tela, tudo aparece expandido e depois
  recolhe para os critérios (decisão do time).

## Mocks e dados de demonstração

- O banco mockado fica no `localStorage` (`STORAGE_KEY` em `services/api.ts`). **Ao mudar
  algo em `src/mocks`, troque a versão da chave**, senão o navegador continua com a cópia antiga.
- `resetMockData()` no console (modo dev) volta aos dados iniciais.
- Os ~400 projetos de `mocks/generatedProjects.ts` são determinísticos e **não** são
  salvos: as análises deles são sintetizadas na leitura. Um projeto gerado que muda (ex.:
  recebe decisão) é copiado para o banco salvo.
- A sessão de login fica em `localStorage["lei-do-bem:session"]` (mock).

## Armadilhas conhecidas

- **dagre** grava `x`/`y` no objeto passado em `setNode`: passe sempre uma cópia dos
  tamanhos (`{ ...NODE_SIZES[kind] }`).
- **dagre** reordena irmãos: usamos `disableOptimalOrderHeuristic` para manter 1.1 acima de 1.2.
- **Enquadrar o grafo**: use `useFrameGraph` (limites calculados do layout final +
  `setViewport`), não `fitView`. O `fitView` do React Flow depende de nós já medidos e falha
  no meio da animação.
- **React Router 7** aplica navegações numa transição: ao atualizar parâmetros em sequência
  rápida, leia `window.location.search` (veja `useProjectFilters`), não o valor do último render.
- **`sr-only` dentro de contêiner com rolagem**: o `<main>` é `relative` para que esses
  elementos absolutos não aumentem o tamanho do documento.
- **Impressão/PDF**: o layout usa `h-dvh` com o `<main>` rolável. Há classes `print:` que
  desfazem isso; mantenha-as ao mexer no layout.

## Escopo

É um projeto de hackathon de 3 dias: prefira a solução simples que funciona na demo. Ideias
maiores vão para `PENDENCIAS.md`, na seção **"Escopo maior"**; o que falta para o app
funcionar vai em **"Essenciais"**.
