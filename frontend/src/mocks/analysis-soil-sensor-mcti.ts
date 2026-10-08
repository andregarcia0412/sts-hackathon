import type { Analysis, Evidence } from "@/domain/types";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";
import { faqMcti, frascati, guiaMcti, inRfb1187 } from "@/mocks/references";

/*
 * EXEMPLO FICTÍCIO: o mesmo projeto do sensor de solo, lido por outro método:
 * os campos do formulário de P&D do MCTI. As evidências são os mesmos trechos
 * do material, organizados como o avaliador do formulário os leria.
 */

/** Reuses an evidence of the Frascati tree (same excerpt, same references) */
const fromFrascati = (criterionId: string, ruleId: string, evidenceId: string, id: string): Evidence => {
  const evidence = soilSensorAnalysis.criteria
    .find((c) => c.id === criterionId)
    ?.rules.find((r) => r.id === ruleId)
    ?.evidences.find((e) => e.id === evidenceId);
  if (!evidence) throw new Error(`Mock evidence not found: ${criterionId}/${ruleId}/${evidenceId}`);
  return { ...evidence, id };
};

const report = { documentId: "doc-2", fileName: "Relatorio_Tecnico_2025_EXEMPLO.pdf" };
const plan = { documentId: "doc-1", fileName: "Plano_de_Projeto_EXEMPLO.pdf" };

export const soilSensorMctiAnalysis: Analysis = {
  id: "an-soil-001-mcti",
  projectId: "p1",
  framework: "mcti_form",
  suggestedCategory: "DE",
  generatedAt: "2026-09-28T13:21:05.000Z",
  criteria: [
    {
      id: "form-novel-element",
      key: "novel_element",
      name: "Elemento tecnologicamente novo",
      score: 80,
      summary:
        "O campo identifica com clareza o elemento novo (compensação de salinidade em sensor de baixo custo) e o compara com o estado da arte.",
      rules: [
        {
          id: "rule-proj-12",
          code: "PROJ-12",
          name: "Elemento tecnologicamente novo",
          score: 84,
          explanation: "O elemento novo está descrito e diferenciado do que existe no mercado.",
          normativeSource: guiaMcti("§6.1"),
          evidences: [
            fromFrascati("crit-novelty", "rule-proj-12", "ev-1", "ev-1"),
            fromFrascati("crit-novelty", "rule-proj-12", "ev-2", "ev-2"),
          ],
        },
        {
          id: "rule-exc-04",
          code: "EXC-04",
          name: "Tecnologia de amplo domínio",
          score: 70,
          explanation: "Partes de amplo domínio estão separadas do núcleo novo, o que o formulário valoriza.",
          normativeSource: guiaMcti("§7 (exclusões)"),
          evidences: [
            fromFrascati("crit-novelty", "rule-exc-04", "ev-2", "ev-1"),
            fromFrascati("crit-novelty", "rule-exc-04", "ev-1", "ev-2"),
          ],
        },
      ],
    },
    {
      id: "form-barrier",
      key: "technological_barrier",
      name: "Barreira tecnológica",
      score: 74,
      summary:
        "A barreira técnica está bem descrita e não se confunde com desafio de mercado, mas faltam registros de todas as tentativas.",
      rules: [
        {
          id: "rule-proj-13",
          code: "PROJ-13",
          name: "Barreira tecnológica",
          score: 80,
          explanation: "Há um problema técnico claro e as abordagens testadas estão descritas.",
          normativeSource: guiaMcti("§6.3"),
          evidences: [
            fromFrascati("crit-uncertainty", "rule-proj-13", "ev-1", "ev-1"),
            fromFrascati("crit-uncertainty", "rule-proj-13", "ev-2", "ev-2"),
            fromFrascati("crit-uncertainty", "rule-proj-13", "ev-3", "ev-3"),
          ],
        },
        {
          id: "rule-exc-05",
          code: "EXC-05",
          name: "Desafio de mercado",
          score: 66,
          explanation:
            "O objetivo comercial (preço abaixo de R$ 150) aparece junto da barreira técnica. O formulário pede que a barreira seja técnica, não de mercado.",
          normativeSource: faqMcti,
          evidences: [
            {
              id: "ev-1",
              title: "Meta de preço apresentada como desafio",
              polarity: "negative",
              explanation:
                "Custo-alvo é desafio de mercado. Ele só conta se o texto mostrar a barreira técnica por trás do custo.",
              projectExcerpt: {
                ...plan,
                page: 3,
                excerpt: "O principal desafio é viabilizar um sensor com custo final inferior a R$ 150.",
              },
              references: [faqMcti],
            },
            {
              id: "ev-2",
              title: "Limite técnico do conversor explicitado",
              polarity: "positive",
              explanation:
                "O texto liga o custo a um limite técnico concreto (resolução do conversor A/D), o que caracteriza barreira tecnológica.",
              projectExcerpt: {
                ...plan,
                page: 6,
                excerpt:
                  "Não há garantia de que a precisão de ±3% seja atingível com o conversor A/D de 12 bits previsto no orçamento.",
              },
              references: [frascati("§2.18"), guiaMcti("§6.3")],
            },
          ],
        },
      ],
    },
    {
      id: "form-methodology",
      key: "methodology",
      name: "Metodologia e métodos",
      score: 57,
      summary:
        "O protocolo de bancada é bom, mas o campo descreve principalmente gestão ágil, e parte dos ensaios pode ser lida como teste de rotina.",
      rules: [
        {
          id: "rule-proj-14",
          code: "PROJ-14",
          name: "Metodologia de P&D",
          score: 58,
          explanation: "A metodologia de pesquisa aparece só parcialmente.",
          normativeSource: frascati("§2.18"),
          evidences: [
            fromFrascati("crit-uncertainty", "rule-proj-14", "ev-2", "ev-1"),
            fromFrascati("crit-uncertainty", "rule-proj-14", "ev-1", "ev-2"),
          ],
        },
        {
          id: "rule-exc-08",
          code: "EXC-08",
          name: "Testes de rotina",
          score: 55,
          explanation:
            "Os ensaios de campo repetem o mesmo protocolo sem nova hipótese; podem ser vistos como validação de rotina.",
          normativeSource: guiaMcti("§7 (exclusões)"),
          evidences: [
            {
              id: "ev-1",
              title: "Ensaios de campo repetidos sem variação",
              polarity: "negative",
              explanation:
                "Repetir o protocolo sem testar hipótese nova aproxima o ensaio de controle de qualidade, que não é P&D.",
              projectExcerpt: {
                ...report,
                page: 9,
                excerpt: "Os experimentos 2, 3 e 4 seguiram o mesmo protocolo e não serão detalhados.",
              },
              references: [guiaMcti("§7"), faqMcti],
            },
            {
              id: "ev-2",
              title: "Ensaio de bancada com hipótese explícita",
              polarity: "positive",
              explanation: "O ensaio de bancada testa uma hipótese definida, o que o diferencia de teste de rotina.",
              projectExcerpt: {
                ...report,
                page: 5,
                excerpt:
                  "Foram preparadas 40 amostras de solo com 5 níveis de salinidade e 8 de umidade; o critério de aceitação é erro absoluto médio inferior a 3%.",
              },
              references: [frascati("§2.18")],
            },
          ],
        },
      ],
    },
    {
      id: "form-scope",
      key: "description_scope",
      name: "Descrição e escopo do projeto",
      score: 50,
      summary:
        "A descrição mistura o núcleo de pesquisa com funcionalidades do aplicativo e com o lote de produção, o que dificulta delimitar o projeto.",
      rules: [
        {
          id: "rule-proj-15",
          code: "PROJ-15",
          name: "Descrição do projeto",
          score: 62,
          explanation: "A hipótese central está descrita, mas o texto se dispersa em funcionalidades.",
          normativeSource: frascati("§2.17"),
          evidences: [
            fromFrascati("crit-creativity", "rule-proj-15", "ev-1", "ev-1"),
            fromFrascati("crit-creativity", "rule-proj-15", "ev-2", "ev-2"),
          ],
        },
        {
          id: "rule-proj-17",
          code: "PROJ-17",
          name: "Projeto como unidade",
          score: 46,
          explanation: "O orçamento inclui custos de produção, o que confunde o escopo do projeto.",
          normativeSource: inRfb1187,
          evidences: [
            fromFrascati("crit-systematic", "rule-proj-17", "ev-1", "ev-1"),
            fromFrascati("crit-systematic", "rule-proj-17", "ev-2", "ev-2"),
          ],
        },
        {
          id: "rule-exc-11",
          code: "EXC-11",
          name: "Software de rotina",
          score: 38,
          explanation: "Firmware e aplicativo aparecem no escopo sem separação clara do núcleo de pesquisa.",
          normativeSource: frascati("§2.68"),
          evidences: [
            fromFrascati("crit-transferability", "rule-exc-11", "ev-2", "ev-1"),
            fromFrascati("crit-transferability", "rule-exc-11", "ev-1", "ev-2"),
          ],
        },
      ],
    },
    {
      id: "form-schedule",
      key: "schedule",
      name: "Cronograma e evolução anual",
      score: 60,
      summary: "Cronograma com marcos técnicos, mas sem relatório de evolução do segundo ano.",
      rules: [
        {
          id: "rule-proj-16",
          code: "PROJ-16",
          name: "Datas e evolução anual",
          score: 60,
          explanation: "Datas claras e marcos técnicos; o ano de 2026 está pouco descrito.",
          normativeSource: inRfb1187,
          evidences: [
            fromFrascati("crit-systematic", "rule-proj-16", "ev-1", "ev-1"),
            fromFrascati("crit-systematic", "rule-proj-16", "ev-2", "ev-2"),
          ],
        },
      ],
    },
  ],
};
