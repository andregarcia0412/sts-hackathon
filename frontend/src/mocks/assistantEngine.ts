import { FRAMEWORK_LABELS, POLARITY_LABELS } from "@/domain/labels";
import {
  SCORE_BANDS,
  SCORE_BAND_LABELS,
  SCORE_BAND_RANGES,
  scoreBand,
} from "@/domain/score";
import { getNodePath, getNodeTitle, indexAnalysis } from "@/domain/tree";
import type {
  AnalysisIndex,
  AnalysisNode,
  CriterionNode,
  EvidenceNode,
  RuleNode,
} from "@/domain/tree";
import type {
  AnswerBlock,
  AnswerSource,
  AssistantAnswer,
  AssistantContext,
} from "@/domain/assistant";

/*
 * MOCK assistant: rule-based answers built only from the analysis data on
 * screen. It follows the same principles as the UI: it never gives a
 * verdict, talks about "força da evidência" and always cites its sources.
 * The real one (ai-microservice) replaces askAssistant() in services/api.ts.
 */

const normalize = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

const bandLabel = (score: number) => SCORE_BAND_LABELS[scoreBand(score)].toLowerCase();

const source = (node: AnalysisNode): AnswerSource => ({
  nodeId: node.id,
  label: `${node.number} ${getNodeTitle(node)}`,
});

const children = <T extends AnalysisNode>(index: AnalysisIndex, node: AnalysisNode) =>
  node.childIds.map((id) => index.get(id)).filter(Boolean) as T[];

const evidenceCounts = (index: AnalysisIndex, rule: RuleNode) => {
  const evidences = children<EvidenceNode>(index, rule);
  const positive = evidences.filter((e) => e.evidence.polarity === "positive").length;
  return { positive, negative: evidences.length - positive };
};

const CALCULATION_NOTE =
  "Nesta versão de demonstração, a nota chega pronta do motor de análise: ela resume as regras e o equilíbrio entre evidências a favor e contra. A fórmula exata de agregação ainda será documentada pelo back-end.";

// ---------------------------------------------------------------------------
// Which node is the question about?
// ---------------------------------------------------------------------------

/**
 * Explicit number ("3.1.2", "critério 4") > rule code ("PROJ-13") >
 * criterion name ("incerteza") > the node selected on screen.
 */
export const resolveTargetNode = (
  question: string,
  index: AnalysisIndex,
  selectedNodeId: string | null,
): AnalysisNode | undefined => {
  const q = normalize(question);
  const nodes = [...index.values()];

  const dotted = q.match(/(?<![\d.])(\d+\.\d+(?:\.\d+)?)(?![\d.])/);
  const criterionNumber = q.match(/criterio\s+(\d+)\b/);
  const number = dotted?.[1] ?? criterionNumber?.[1];
  const byNumber = number && nodes.find((n) => n.number === number);
  if (byNumber) return byNumber;

  const code = q.match(/\b((?:proj|exc|doc)-\d+)\b/)?.[1];
  if (code) {
    const rules = nodes.filter(
      (n): n is RuleNode => n.kind === "rule" && n.rule.code.toLowerCase() === code,
    );
    const selectedCriterion = selectedNodeId?.split(".")[0];
    const match = rules.find((r) => r.criterion.id === selectedCriterion) ?? rules[0];
    if (match) return match;
  }

  const byName = nodes.find(
    (n) => n.kind === "criterion" && q.includes(normalize(n.criterion.name).slice(0, 6)),
  );
  if (byName) return byName;

  return selectedNodeId ? index.get(selectedNodeId) : undefined;
};

// ---------------------------------------------------------------------------
// Answers
// ---------------------------------------------------------------------------

const criteriaOverview = (index: AnalysisIndex) =>
  [...index.values()]
    .filter((n): n is CriterionNode => n.kind === "criterion")
    .map((n) => `${n.number}. ${n.criterion.name}: ${n.criterion.score}/100 (${bandLabel(n.criterion.score)})`);

const explainScore = (index: AnalysisIndex, node: AnalysisNode): AssistantAnswer => {
  if (node.kind === "criterion") {
    const rules = children<RuleNode>(index, node);
    return {
      blocks: [
        {
          type: "text",
          text: `O critério ${node.number}. ${node.criterion.name} tem força da evidência ${node.criterion.score}/100 (${bandLabel(node.criterion.score)}).`,
        },
        { type: "text", text: node.criterion.summary },
        { type: "text", text: "Ela se apoia nestas regras:" },
        {
          type: "list",
          items: rules.map((r) => {
            const { positive, negative } = evidenceCounts(index, r);
            return `${r.number} ${r.rule.code} ${r.rule.name}: ${r.rule.score}/100 (${bandLabel(r.rule.score)}), ${positive} evidência(s) a favor e ${negative} contra`;
          }),
        },
        { type: "text", text: CALCULATION_NOTE },
      ],
      sources: [source(node), ...rules.map(source)],
      suggestions: [
        `Quais evidências pesam contra em ${node.criterion.name}?`,
        ...(rules[0] ? [`Como a nota da regra ${rules[0].number} foi calculada?`] : []),
        "O que significa força da evidência?",
      ],
    };
  }

  if (node.kind === "rule") {
    const evidences = children<EvidenceNode>(index, node);
    return {
      blocks: [
        {
          type: "text",
          text: `A regra ${node.number} ${node.rule.code} (${node.rule.name}) tem força da evidência ${node.rule.score}/100 (${bandLabel(node.rule.score)}).`,
        },
        { type: "text", text: node.rule.explanation },
        { type: "text", text: `Base normativa: ${node.rule.normativeSource.label}. Evidências consideradas:` },
        {
          type: "list",
          items: evidences.map(
            (e) => `${e.number} ${e.evidence.title} (${POLARITY_LABELS[e.evidence.polarity].toLowerCase()})`,
          ),
        },
        { type: "text", text: CALCULATION_NOTE },
      ],
      sources: [source(node), ...evidences.map(source)],
      suggestions: [
        ...(evidences[0] ? [`Como a evidência ${evidences[0].number} foi formada?`] : []),
        `Qual a base normativa da regra ${node.rule.code}?`,
      ],
    };
  }

  const rule = index.get(node.parentId!) as RuleNode;
  return {
    blocks: [
      {
        type: "text",
        text: `Evidências não têm nota própria: são classificadas como positivas ou negativas e alimentam a nota da regra ${rule.number} ${rule.rule.code} (${rule.rule.score}/100).`,
      },
      ...explainEvidence(index, node).blocks,
    ],
    sources: [source(node), source(rule)],
    suggestions: [`Como a nota da regra ${rule.number} foi calculada?`],
  };
};

const explainEvidence = (index: AnalysisIndex, node: EvidenceNode): AssistantAnswer => {
  const rule = index.get(node.parentId!) as RuleNode;
  const criterion = index.get(rule.parentId!) as CriterionNode;
  const { evidence } = node;
  const inFavor = evidence.polarity === "positive";
  const excerpt = evidence.projectExcerpt;

  const blocks: AnswerBlock[] = [
    {
      type: "text",
      text: `${node.number} ${evidence.title} é uma evidência ${inFavor ? "positiva" : "negativa"} da regra ${rule.number} ${rule.rule.code} (${rule.rule.name}), no critério ${criterion.number}. ${criterion.criterion.name}.`,
    },
    {
      type: "text",
      text: `Ela é formada por três ligações: o trecho do material do projeto, a regra que ele ${inFavor ? "sustenta" : "enfraquece"} e as referências normativas. Por que conta ${inFavor ? "a favor" : "contra"}: ${evidence.explanation}`,
    },
    excerpt
      ? {
          type: "quote",
          text: excerpt.excerpt,
          caption: `${excerpt.fileName ?? "Descrição em texto livre"}${excerpt.page !== undefined ? `, p. ${excerpt.page}` : ""}`,
        }
      : {
          type: "text",
          text: "Ela não se apoia num trecho: aponta a ausência de informação no material enviado.",
        },
  ];
  if (evidence.references.length > 0) {
    blocks.push(
      { type: "text", text: "Referências:" },
      { type: "list", items: evidence.references.map((r) => r.label) },
    );
  }

  return {
    blocks,
    sources: [source(node), source(rule)],
    suggestions: [
      `Como a nota da regra ${rule.number} foi calculada?`,
      `Quais evidências pesam contra em ${criterion.criterion.name}?`,
    ],
  };
};

const explainTraceability = (index: AnalysisIndex, node?: AnalysisNode): AssistantAnswer => {
  const base: AnswerBlock = {
    type: "text",
    text: "Toda nota leva, em até dois cliques, à regra que a gerou, ao trecho do documento do projeto e à referência normativa (lei, decreto, Manual de Frascati).",
  };
  if (!node) {
    return {
      blocks: [
        base,
        {
          type: "text",
          text: "Selecione um item no grafo ou cite um número (ex.: 3.1.1) para eu mostrar o caminho completo dele.",
        },
      ],
      sources: [],
      suggestions: ["Como a evidência 3.1.1 foi formada?"],
    };
  }

  const path = getNodePath(index, node.id);
  const rule = path.find((n): n is RuleNode => n.kind === "rule");
  const references =
    node.kind === "evidence"
      ? node.evidence.references
      : rule
        ? [rule.rule.normativeSource]
        : [];

  return {
    blocks: [
      base,
      {
        type: "text",
        text: `Caminho de ${node.number}: ${["Frascati", ...path.map((n) => `${n.number} ${getNodeTitle(n)}`)].join(" › ")}.`,
      },
      ...(references.length > 0
        ? ([
            { type: "text", text: "Referências ligadas a este item:" },
            { type: "list", items: references.map((r) => (r.url ? `${r.label} (${r.url})` : r.label)) },
          ] as AnswerBlock[])
        : [
            {
              type: "text",
              text: "Um critério reúne as referências das suas regras: escolha uma regra para ver a base normativa.",
            } as AnswerBlock,
          ]),
    ],
    sources: path.map(source),
    suggestions: [],
  };
};

const weakestPoints = (index: AnalysisIndex, node?: AnalysisNode): AssistantAnswer => {
  if (node?.kind === "criterion") {
    const rules = children<RuleNode>(index, node).sort((a, b) => a.rule.score - b.rule.score);
    return {
      blocks: [
        { type: "text", text: `Em ${node.criterion.name}, as regras com evidência mais fraca são:` },
        {
          type: "list",
          items: rules.map((r) => `${r.number} ${r.rule.code} ${r.rule.name}: ${r.rule.score}/100 (${bandLabel(r.rule.score)})`),
        },
      ],
      sources: rules.map(source),
      suggestions: [`Quais evidências pesam contra em ${node.criterion.name}?`],
    };
  }

  const criteria = [...index.values()]
    .filter((n): n is CriterionNode => n.kind === "criterion")
    .sort((a, b) => a.criterion.score - b.criterion.score)
    .slice(0, 3);
  const weakest = criteria[0];
  return {
    blocks: [
      {
        type: "text",
        text: "Os cinco critérios precisam ser atendidos juntos, então vale olhar primeiro para os de evidência mais fraca:",
      },
      {
        type: "list",
        items: criteria.map((c) => `${c.number}. ${c.criterion.name}: ${c.criterion.score}/100 (${bandLabel(c.criterion.score)})`),
      },
      { type: "text", text: `${weakest.criterion.name}: ${weakest.criterion.summary}` },
    ],
    sources: criteria.map(source),
    suggestions: [
      `Quais evidências pesam contra em ${weakest.criterion.name}?`,
      `Como a nota de ${weakest.criterion.name} foi calculada?`,
    ],
  };
};

const negativeEvidences = (index: AnalysisIndex, node?: AnalysisNode): AssistantAnswer => {
  const scope = node ? getNodePath(index, node.id)[0] : undefined;
  const negatives = [...index.values()].filter(
    (n): n is EvidenceNode =>
      n.kind === "evidence" &&
      n.evidence.polarity === "negative" &&
      (!scope || n.id.startsWith(`${scope.id}.`)),
  );
  const where = scope?.kind === "criterion" ? ` em ${scope.criterion.name}` : " na análise";

  if (negatives.length === 0) {
    return {
      blocks: [{ type: "text", text: `Não há evidências negativas${where}.` }],
      sources: scope ? [source(scope)] : [],
      suggestions: [],
    };
  }
  return {
    blocks: [
      { type: "text", text: `Evidências que pesam contra${where}:` },
      {
        type: "list",
        items: negatives.slice(0, 6).map((e) => `${e.number} ${e.evidence.title}: ${e.evidence.explanation}`),
      },
      ...(negatives.length > 6
        ? [{ type: "text", text: `E mais ${negatives.length - 6}. Filtre por critério para ver todas.` } as AnswerBlock]
        : []),
    ],
    sources: negatives.slice(0, 6).map(source),
    suggestions: negatives[0] ? [`Como a evidência ${negatives[0].number} foi formada?`] : [],
  };
};

const noVerdict = (index: AnalysisIndex): AssistantAnswer => ({
  blocks: [
    {
      type: "text",
      text: "Não posso dizer se o projeto deve ser enquadrado: a decisão é do analista, e o enquadramento oficial cabe ao MCTI. O que posso fazer é resumir a força da evidência em cada critério:",
    },
    { type: "list", items: criteriaOverview(index) },
    {
      type: "text",
      text: "Os cinco critérios precisam ser atendidos juntos; os de evidência fraca merecem mais atenção na justificativa.",
    },
  ],
  sources: [],
  suggestions: ["Quais os pontos fracos da análise?"],
});

const scoreConcept = (): AssistantAnswer => ({
  blocks: [
    {
      type: "text",
      text: "A nota (0–100) mede a força da evidência encontrada no material: o quanto os documentos sustentam cada critério ou regra. Não é a probabilidade de aprovação, porque não existe dado oficial para calibrar isso.",
    },
    {
      type: "list",
      items: SCORE_BANDS.map((band) => `${SCORE_BAND_LABELS[band]}: ${SCORE_BAND_RANGES[band]}`),
    },
  ],
  sources: [],
  suggestions: ["Quais os pontos fracos da análise?"],
});

const help = (context: AssistantContext): AssistantAnswer => ({
  blocks: [
    {
      type: "text",
      text: `Sou um assistente para a análise preliminar (critérios de ${FRAMEWORK_LABELS[context.analysis.framework]}). Posso explicar como cada nota se forma, de onde vem cada evidência e qual a base normativa. Não decido pelo analista.`,
    },
    {
      type: "text",
      text:
        context.screen === "analysis"
          ? "Selecione um item no grafo ou na árvore e pergunte sobre ele, ou cite um número (ex.: 3.1) ou código (ex.: PROJ-13)."
          : "Cite um número do documento (ex.: 3.1.1) ou um código de regra (ex.: PROJ-13) na pergunta.",
    },
  ],
  sources: [],
  suggestions: starterSuggestions(context),
});

const needsTarget = (index: AnalysisIndex): AssistantAnswer => ({
  blocks: [
    {
      type: "text",
      text: "Sobre qual item? Selecione um critério, regra ou evidência no grafo, ou cite o número (ex.: 3.1) ou o código (ex.: PROJ-13). Visão geral:",
    },
    { type: "list", items: criteriaOverview(index) },
  ],
  sources: [],
  suggestions: ["Como a nota de Incerteza foi calculada?", "Quais os pontos fracos da análise?"],
});

// ---------------------------------------------------------------------------

export const starterSuggestions = (context: AssistantContext): string[] => {
  const selected = context.selectedNodeId
    ? indexAnalysis(context.analysis).get(context.selectedNodeId)
    : undefined;
  const aboutSelection = {
    criterion: "Como a nota deste critério foi calculada?",
    rule: "Como a nota desta regra foi calculada?",
    evidence: "Como esta evidência foi formada?",
  };
  return [
    ...(selected ? [aboutSelection[selected.kind]] : []),
    "Quais os pontos fracos da análise?",
    "O que significa força da evidência?",
    "Como funciona a rastreabilidade?",
  ];
};

export const answerQuestion = (
  question: string,
  context: AssistantContext,
): AssistantAnswer => {
  const index = indexAnalysis(context.analysis);
  const q = normalize(question);
  const target = resolveTargetNode(question, index, context.selectedNodeId);

  if (/(aprovad|reprovad|vai passar|veredito|posso aprovar|e enquadravel|sera enquadrad|deve ser enquadrad)/.test(q)) {
    return noVerdict(index);
  }
  if (/(o que (e|significa)|significado|como interpretar).*(forca|faixa|nota|escore)/.test(q)) {
    return scoreConcept();
  }
  if (/(contra|negativ)/.test(q)) return negativeEvidences(index, target);
  if (/(fraco|fraca|pior|atencao|melhorar|lacuna)/.test(q)) return weakestPoints(index, target);
  if (/(rastreab|fonte|referencia|norma|base legal|frascati)/.test(q)) {
    return explainTraceability(index, target);
  }
  if (/(evidencia|trecho|formad|origem|de onde|pagina)/.test(q)) {
    if (target?.kind === "evidence") return explainEvidence(index, target);
    if (target) return explainScore(index, target);
    return needsTarget(index);
  }
  if (/(nota|escore|score|pontua|calcul|forca)/.test(q)) {
    return target ? explainScore(index, target) : needsTarget(index);
  }
  if (target) return explainScore(index, target);
  return help(context);
};
