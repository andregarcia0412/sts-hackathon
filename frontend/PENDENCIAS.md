# Pendências para a versão final

Pontos deixados para depois durante o desenvolvimento do esqueleto. Revisar antes
de fechar o app ou uma versão de demonstração.

## Conteúdo e terminologia

- [ ] **Conferir as referências normativas dos mocks.** Algumas seções foram escritas
      como placeholder e não foram verificadas: "Guia Prático da Lei do Bem (MCTI) §7
      (exclusões)", "Manual de Frascati §2.49" e "§2.68". Também confirmar se as URLs do
      Planalto (Lei 11.196/2005 e Decreto 5.798/2006) abrem o texto certo.
      Arquivos: `src/mocks/references.ts`, `src/mocks/analysis-*.ts`.
- [ ] **Nomes das classificações PB / PA / DE.** Hoje: "Pesquisa básica", "Pesquisa
      aplicada", "Desenvolvimento experimental" (Frascati + Decreto 5.798/2006, art. 2º).
      O decreto fala em "pesquisa básica **dirigida**". Os nomes devem mudar; ajustar em
      `src/domain/labels.ts`.
- [ ] **Exclusões (EXC-xx)** ficam como regras dentro dos critérios (decidido). Revisitar
      se o back-end mandar um grupo próprio.
- [ ] Confirmar com o back-end a **escala da nota** (hoje 0–100, faixas em
      `src/domain/score.ts`) e os **formatos de upload** aceitos (hoje PDF, DOCX, TXT).

## Integração

- [ ] Trocar os mocks pela API real em `src/services/api.ts` (projetos, análise, decisões).
- [ ] **Trilha de decisões** em banco de dados (hoje `localStorage`). Manter o
      comportamento de só acrescentar registros.
- [ ] **Chatbot:** trocar as respostas mockadas (`askAssistant` em `src/services/api.ts`)
      pela integração com o ai-microservice. Manter as regras: nunca dar veredito,
      falar em "força da evidência" e sempre citar a fonte.
- [ ] Upload real dos arquivos (hoje só os metadados são guardados).

## Técnico

- [ ] Bundle passa de 500 kB por causa do React Flow: carregar as telas sob demanda
      (`React.lazy` nas rotas de análise e decisão).
- [ ] Fontes: os tokens citam Inter e Source Serif, mas elas não são carregadas
      (o navegador usa a fonte do sistema). Resolver junto com o design final.
- [ ] Aplicar o visual de alta fidelidade do designer (tokens em `src/index.css`,
      cards do grafo em `src/features/analysis/graph/GraphNodes.tsx`).

## Fora do front-end (avisar o time)

- [ ] O commit inicial do `ai-microservice` incluiu arquivos `__pycache__/*.pyc`;
      ajustar o `.gitignore` de lá.
