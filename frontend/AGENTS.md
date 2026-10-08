# AGENTS.md: front-end

Guia para agentes de IA (e pessoas) que forem mexer nesta pasta. Para a visão geral do
produto e das telas, leia o `README.md`. O que ficou para depois está no `TODOs.md`.

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
npm run test:e2e   # Playwright (e2e/), sobe o Vite na porta 5180
```

Antes de considerar uma tarefa pronta: `npm test`, `npm run lint` sem avisos, `npm run build`,
`npm run test:e2e` e conferir a tela no navegador (login de demonstração: qualquer analista,
qualquer senha).

### Testes ponta a ponta (`e2e/`)

- Escreva como uma pessoa testaria: localize por papel e texto visíveis (`getByRole`,
  `getByLabel`), digite com `typeLikeAPerson`, não pule etapas por URL nas jornadas.
- Use `test` e `expect` de `e2e/fixtures.ts`: o teste falha se a página registrar erro
  no console. Sessão sem passar pelo login: `signInAs(page, USERS.ana)`.
- A lista de projetos mantém a página anterior enquanto carrega e o grafo anima: espere
  o resultado esperado (`expect.poll`, `toHaveCount`), nunca leia a tela logo após um clique.
- Mudou um texto ou rótulo da interface? Atualize os testes que o usam.

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
                 types.ts · tree.ts · score.ts · qualitative.ts · reviews.ts · evidence.ts
                 frameworks.ts · contestations.ts · assistant.ts
  mocks/         dados FICTÍCIOS e motores mockados (chatbot, debate, reanálise, explicação
                 da nota, ~400 projetos gerados, filtros da lista)
  services/      api.ts = ÚNICA camada de dados · queries.ts = hooks do TanStack Query
  features/      projects · analysis (detail, graph) · decision · assistant · auth
  components/    layout (AppLayout, ProjectHeader), icons/ (Material do Figma) e UI
                 compartilhada (Tag, SegmentedControl, ReviewTag, ScoreBreakdown…)
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
  filtros da lista de projetos também. É a fonte de verdade da seleção: o painel de
  detalhamento abre o critério, a regra e a evidência a partir dela.
- **Um projeto tem uma análise por método** (`FRAMEWORKS` em `domain/frameworks.ts`). Para
  incluir um método, adicione-o ali e nos mocks/back-end.
- **Faixas de nota** só em `scoreBand()` (`domain/score.ts`).
- **Contestação**: `open` → reanálise → `resolved` (`accepted` ajusta a análise via
  `applyAdjustments`; `maintained` não muda nada). As análises devolvidas pela API já vêm
  com os ajustes aplicados.
- **Rótulos qualitativos** (Sustentado, Parcialmente, Contraditório, Sem evidência…) só em
  `domain/qualitative.ts`, derivados da nota e das evidências. Critérios usam a palavra de
  cada um, como no design (`criterionStatusInfo`: "Demonstrada no recorte", "Investigada",
  "Documentada"…); para um critério novo, inclua a chave em `CRITERION_WORDS`. O número
  0–100 continua visível no detalhamento (decisão do time).
- **Decisão final**: `eligible` / `with_reservations` / `not_eligible` → Elegível / Com
  ressalvas / Não elegível.
- **Lista de projetos**: os cards de situação são o filtro de status; a barra tem critério
  mais fraco, decisão, período de envio e ordem (o botão redondo conta e limpa os filtros).
- **Grafo**: visão "Critério" (padrão: um critério inteiro, como no Figma) e "Mapa geral"
  (os 5 critérios; na primeira abertura expande tudo e depois recolhe).
- **Decisão do analista por regra** (`RuleDecision`) e **triagem de evidência**
  (`EvidenceReview`, descartar pede motivo): só acrescentadas; a mais recente por nó vale
  (`domain/reviews.ts`). Um critério está "decidido" quando todas as regras têm nota.

## Design system (Figma)

- Tokens em `src/index.css` com o nome da variável do Figma em comentário (`neutro/900`,
  `marca/primaria`, `estado/positiva`…). Use os nomes semânticos (`text-fg`, `bg-action`,
  `text-state-positive`), nunca hex solto.
- Fonte **Heebo** (Google Fonts, `index.html`). Ícones grandes (24px) são Material,
  copiados do Figma para `components/icons/MaterialIcons.tsx`; os pequenos (12–14px) são
  Lucide. O designer usa MUI no Figma, mas **não** instalamos a lib: os componentes são
  simples e reproduzidos com Tailwind.
- "Etiqueta" = `<Tag tone label size>` (sempre ícone + texto). Botões: `.btn-primary`
  (pílula vinho), `.btn-secondary`, `.btn-chip`, `.btn-link`.
- Texto cinza claro do Figma (`#979797`) não tem contraste suficiente para texto: usamos
  `text-fg-muted` (`#646464`) nesses casos.
- Os cards de situação da lista usam cores próprias do design (laranja, azul, verde:
  `--color-card-*`), fora da paleta da marca, por decisão do time.

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
maiores vão para `TODOs.md`, na seção **"Escopo maior"**; o que falta para o app
funcionar vai em **"Essenciais"**.
