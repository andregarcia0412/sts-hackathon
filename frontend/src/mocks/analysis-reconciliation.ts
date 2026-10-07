import type { Analysis, Decision, ProjectDocument } from "@/domain/types";
import { faqMcti, frascati, guiaMcti, inRfb1187 } from "@/mocks/references";

/*
 * EXEMPLO FICTÍCIO: projeto mais fraco, já decidido pelo analista.
 * Serve para a lista (status "decidido") e para a trilha da tela de decisão.
 */

export const reconciliationDocuments: ProjectDocument[] = [
  {
    id: "doc-1",
    fileName: "Descricao_Projeto_Conciliacao_EXEMPLO.pdf",
    mimeType: "application/pdf",
    sizeBytes: 912_004,
    uploadedAt: "2026-09-15T10:02:00.000Z",
  },
];

const description = {
  documentId: "doc-1",
  fileName: "Descricao_Projeto_Conciliacao_EXEMPLO.pdf",
};

export const reconciliationAnalysis: Analysis = {
  id: "an-recon-001",
  projectId: "p2",
  framework: "frascati",
  generatedAt: "2026-09-15T10:09:12.000Z",
  criteria: [
    {
      id: "crit-novelty",
      key: "novelty",
      name: "Novidade",
      score: 32,
      summary:
        "A conciliação automática de extratos já é oferecida por várias soluções de mercado; o documento não aponta o que é novo para o setor.",
      rules: [
        {
          id: "rule-exc-04",
          code: "EXC-04",
          name: "Tecnologia de amplo domínio",
          score: 28,
          explanation:
            "OCR e regras de correspondência são tecnologias de amplo domínio.",
          normativeSource: guiaMcti("§7 (exclusões)"),
          evidences: [
            {
              id: "ev-1",
              title: "OCR de biblioteca pronta",
              polarity: "negative",
              explanation:
                "O reconhecimento de texto usa biblioteca de código aberto sem adaptação técnica descrita.",
              projectExcerpt: {
                ...description,
                page: 2,
                excerpt:
                  "A leitura dos comprovantes utilizará o motor de OCR Tesseract.",
              },
              references: [guiaMcti("§7")],
            },
            {
              id: "ev-2",
              title: "Nenhuma comparação com o mercado",
              polarity: "negative",
              explanation:
                "Sem comparação com soluções existentes, não há como sustentar novidade para o setor.",
              references: [frascati("§2.15")],
            },
          ],
        },
      ],
    },
    {
      id: "crit-creativity",
      key: "creativity",
      name: "Criatividade",
      score: 41,
      summary:
        "Há uma ideia de correspondência aproximada por valor e data, mas ela é descrita como ajuste de regras de negócio.",
      rules: [
        {
          id: "rule-proj-15",
          code: "PROJ-15",
          name: "Descrição do projeto",
          score: 41,
          explanation:
            "A descrição é funcional (o que o sistema faz), sem explicar a solução técnica.",
          normativeSource: frascati("§2.17"),
          evidences: [
            {
              id: "ev-1",
              title: "Correspondência aproximada",
              polarity: "positive",
              explanation:
                "A heurística para lançamentos parcelados pode ter algum componente original.",
              projectExcerpt: {
                ...description,
                page: 3,
                excerpt:
                  "Lançamentos parcelados serão associados por janela de datas e soma aproximada dos valores.",
              },
              references: [frascati("§2.17")],
            },
            {
              id: "ev-2",
              title: "Descrição só funcional",
              polarity: "negative",
              explanation:
                "O documento lista funcionalidades e não o problema técnico a ser resolvido.",
              projectExcerpt: {
                ...description,
                page: 1,
                excerpt:
                  "O sistema permitirá importar extratos, cadastrar regras e gerar relatórios de conciliação.",
              },
              references: [faqMcti],
            },
          ],
        },
      ],
    },
    {
      id: "crit-uncertainty",
      key: "uncertainty",
      name: "Incerteza",
      score: 22,
      summary:
        "Não há risco técnico declarado: o resultado esperado é conhecido desde o início.",
      rules: [
        {
          id: "rule-proj-13",
          code: "PROJ-13",
          name: "Barreira tecnológica",
          score: 22,
          explanation: "Nenhuma barreira tecnológica é identificada.",
          normativeSource: guiaMcti("§6.3"),
          evidences: [
            {
              id: "ev-1",
              title: "Prazo e custo previsíveis",
              polarity: "negative",
              explanation:
                "O próprio documento afirma que a entrega é previsível, o que contradiz o critério de incerteza.",
              projectExcerpt: {
                ...description,
                page: 4,
                excerpt:
                  "A equipe já domina as tecnologias envolvidas, o que garante a entrega no prazo de seis meses.",
              },
              references: [frascati("§2.18")],
            },
            {
              id: "ev-2",
              title: "Ausência de hipóteses testadas",
              polarity: "negative",
              explanation: "Não há hipóteses, experimentos ou alternativas descartadas.",
              references: [faqMcti],
            },
          ],
        },
      ],
    },
    {
      id: "crit-systematic",
      key: "systematic",
      name: "Sistematização",
      score: 70,
      summary:
        "O projeto tem cronograma, orçamento e equipe bem definidos, ainda que voltados a entrega de produto.",
      rules: [
        {
          id: "rule-proj-16",
          code: "PROJ-16",
          name: "Datas e evolução anual",
          score: 70,
          explanation: "Cronograma e orçamento detalhados por mês.",
          normativeSource: inRfb1187,
          evidences: [
            {
              id: "ev-1",
              title: "Cronograma mensal",
              polarity: "positive",
              explanation: "Atividades, responsáveis e custos por mês.",
              projectExcerpt: {
                ...description,
                page: 5,
                excerpt: "Mês 1–2: importação de extratos; mês 3–4: OCR; mês 5–6: relatórios.",
              },
              references: [frascati("§2.19")],
            },
            {
              id: "ev-2",
              title: "Marcos de produto, não de pesquisa",
              polarity: "negative",
              explanation:
                "Os marcos são funcionalidades entregues, e não resultados de experimentos.",
              references: [faqMcti],
            },
          ],
        },
      ],
    },
    {
      id: "crit-transferability",
      key: "transferability",
      name: "Transferibilidade",
      score: 25,
      summary:
        "Sem registros técnicos além da descrição funcional; nada que permita reprodução por terceiros.",
      rules: [
        {
          id: "rule-exc-11",
          code: "EXC-11",
          name: "Software de rotina",
          score: 25,
          explanation:
            "O projeto se enquadra na descrição de software de rotina (sistema de gestão).",
          normativeSource: frascati("§2.68"),
          evidences: [
            {
              id: "ev-1",
              title: "Sistema de gestão convencional",
              polarity: "negative",
              explanation:
                "Cadastros, importação e relatórios são exemplos clássicos de software de rotina.",
              projectExcerpt: {
                ...description,
                page: 1,
                excerpt:
                  "O sistema permitirá importar extratos, cadastrar regras e gerar relatórios de conciliação.",
              },
              references: [frascati("§2.68")],
            },
            {
              id: "ev-2",
              title: "Nenhum relatório técnico",
              polarity: "negative",
              explanation: "Não há relatório técnico, só a descrição comercial.",
              references: [frascati("§2.20")],
            },
          ],
        },
      ],
    },
  ],
};

export const reconciliationDecisions: Decision[] = [
  {
    projectId: "p2",
    analysisId: "an-recon-001",
    outcome: "not_eligible",
    justification:
      "Projeto de software de gestão com tecnologias de amplo domínio (OCR pronto, regras de negócio). Não há barreira tecnológica nem incerteza declarada. A heurística de correspondência aproximada não basta para caracterizar P&D. EXEMPLO FICTÍCIO.",
    analystName: "Analista Exemplo",
    decidedAt: "2026-09-16T14:30:00.000Z",
    ruleOverrides: [
      {
        ruleId: "crit-creativity.rule-proj-15",
        note: "Considero a nota de criatividade otimista: a heurística é ajuste de regra de negócio.",
      },
    ],
  },
];
