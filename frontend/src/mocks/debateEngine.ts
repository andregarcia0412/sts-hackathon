import type {
  AnswerBlock,
  AssistantAnswer,
  AssistantContext,
} from "@/domain/assistant";
import {
  CONTESTATION_REASON_LABELS,
  CONTESTATION_REASONS_BY_KIND as REASONS_BY_KIND,
} from "@/domain/labels";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";
import { getNodeTitle, indexAnalysis } from "@/domain/tree";
import type {
  AnalysisIndex,
  AnalysisNode,
  EvidenceNode,
} from "@/domain/tree";
import type { ContestationReason } from "@/domain/types";
import { formatPoints } from "@/lib/scoreFormat";
import { contestationChanges } from "@/mocks/reanalysis";

/*
 * MOCK debate: the analyst contests a node and the "model" defends or
 * reconsiders its reading. It never changes a score by itself: it shows the
 * basis, simulates the effect of the analyst's claim and offers to record a
 * contestation (which goes to the decision trail).
 */

const normalize = (text: string) =>
  text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

const band = (score: number) => SCORE_BAND_LABELS[scoreBand(score)].toLowerCase();
const nodeLabel = (node: AnalysisNode) => `${node.number} ${getNodeTitle(node)}`;
const source = (node: AnalysisNode) => ({ nodeId: node.id, label: nodeLabel(node) });

export const detectReason = (
  message: string,
  kind: AnalysisNode["kind"],
): ContestationReason => {
  const byLabel = (Object.entries(CONTESTATION_REASON_LABELS) as [ContestationReason, string][])
    .find(([, label]) => label === message.trim());
  if (byLabel) return byLabel[0];

  const q = normalize(message);
  if (kind === "evidence" && /(polarid|deveria ser (positiva|negativa)|a favor|conta contra|e positiva|e negativa)/.test(q)) {
    return "polarity";
  }
  if (/(alt[ao] demais|exagerad|superestim|generos|muito alt)/.test(q)) return "score_too_high";
  if (/(baix[ao] demais|subestim|injust|rigoros|muito baix)/.test(q)) return "score_too_low";
  if (/(trecho|nao diz|fora de contexto|pagina errada|nao sustenta|leu errado)/.test(q)) return "wrong_excerpt";
  if (/(faltou|nao considerou|ignorou|esqueceu|faltando|nao viu)/.test(q)) return "missing_evidence";
  return "other";
};

const reasonChips = (node: AnalysisNode) =>
  REASONS_BY_KIND[node.kind].map((reason) => CONTESTATION_REASON_LABELS[reason]);

const recordAction = (node: AnalysisNode, reason: ContestationReason) => [
  { type: "record-contestation" as const, nodeId: node.id, reason },
];

// ---------------------------------------------------------------------------

const basisBlocks = (index: AnalysisIndex, node: AnalysisNode): AnswerBlock[] => {
  if (node.kind === "evidence") {
    const excerpt = node.evidence.projectExcerpt;
    return [
      {
        type: "text",
        text: `Classifiquei como evidência ${node.evidence.polarity === "positive" ? "positiva" : "negativa"} da regra ${node.rule.code}: ${node.evidence.explanation}`,
      },
      excerpt
        ? {
            type: "quote",
            text: excerpt.excerpt,
            caption: `${excerpt.fileName ?? "Descrição em texto livre"}${excerpt.page !== undefined ? `, p. ${excerpt.page}` : ""}`,
          }
        : { type: "text", text: "Ela não tem trecho: aponta a ausência de informação no material." },
    ];
  }
  const target = node.kind === "criterion" ? node.criterion : node.rule;
  const description = node.kind === "criterion" ? node.criterion.summary : node.rule.explanation;
  return [
    {
      type: "text",
      text: `Dei ${target.score}/100 (${band(target.score)}). ${description}`,
    },
    ...(node.childIds.length
      ? [
          {
            type: "list" as const,
            items: node.childIds.map((id) => {
              const child = index.get(id)!;
              return child.kind === "rule"
                ? `${child.number} ${child.rule.code}: ${child.rule.score}/100`
                : `${child.number} ${getNodeTitle(child)} (${child.kind === "evidence" && child.evidence.polarity === "positive" ? "a favor" : "contra"})`;
            }),
          },
        ]
      : []),
  ];
};

export const debateOpening = (context: AssistantContext, nodeId: string): AssistantAnswer => {
  const index = indexAnalysis(context.analysis);
  const node = index.get(nodeId);
  if (!node) {
    return { blocks: [{ type: "text", text: "Não encontrei esse item na análise." }], sources: [], suggestions: [] };
  }
  return {
    blocks: [
      { type: "text", text: `Vamos rever ${nodeLabel(node)}. Esta é a base da minha leitura:` },
      ...basisBlocks(index, node),
      {
        type: "text",
        text: "O que você acha que está errado? Escolha um motivo ou explique com suas palavras (se puder, cite arquivo e página).",
      },
    ],
    sources: [source(node)],
    suggestions: reasonChips(node),
  };
};

// ---------------------------------------------------------------------------

const replyPolarity = (context: AssistantContext, node: AnalysisNode): AnswerBlock[] => {
  if (node.kind !== "evidence") {
    return [{ type: "text", text: "Polaridade vale para evidências. Escolha uma evidência específica para contestar se ela conta a favor ou contra." }];
  }
  const flipped = node.evidence.polarity === "positive" ? "negativa" : "positiva";
  // Same calculation the reanalysis applies if the contestation is accepted
  const changes = contestationChanges(context.analysis, { nodeId: node.id, reason: "polarity" });
  const scoreChanges = changes.filter((c) => c.field === "score");
  return [
    {
      type: "text",
      text: `Posso ter lido errado. Mantive como ${node.evidence.polarity === "positive" ? "positiva" : "negativa"} porque: ${node.evidence.explanation}`,
    },
    scoreChanges.length
      ? {
          type: "text",
          text: `Simulação: se ela fosse ${flipped}, ${scoreChanges
            .map((c) => `${c.nodeLabel} iria de ${c.before} para ${c.after} (${band(c.after as number)})`)
            .join(" e ")}.`,
        }
      : { type: "text", text: "Não consigo simular o efeito desta mudança na nota." },
  ];
};

const replyScore = (index: AnalysisIndex, node: AnalysisNode, direction: "high" | "low"): AnswerBlock[] => {
  if (node.kind === "evidence") {
    return [{ type: "text", text: "Evidências não têm nota própria. Se ela pesa demais ou de menos, conteste a regra dela, ou a polaridade desta evidência." }];
  }
  const target = node.kind === "criterion" ? node.criterion : node.rule;
  const factors = (target.scoreExplanation?.factors ?? [])
    .filter((f) => (direction === "high" ? f.points > 0 : f.points < 0))
    .sort((a, b) => (direction === "high" ? b.points - a.points : a.points - b.points))
    .slice(0, 3);
  const label = (refId?: string, fallback = "") => {
    const child = refId ? index.get(`${node.id}.${refId}`) : undefined;
    return child ? nodeLabel(child) : fallback;
  };

  const blocks: AnswerBlock[] = [
    {
      type: "text",
      text: direction === "high"
        ? `É possível que eu tenha sido generoso. O que mais sobe esta nota (${target.score}/100):`
        : `É possível que eu tenha sido rigoroso. O que mais derruba esta nota (${target.score}/100):`,
    },
  ];
  if (factors.length) {
    blocks.push({ type: "list", items: factors.map((f) => `${label(f.refId, f.label)}: ${formatPoints(f.points)}`) });
  } else {
    blocks.push({ type: "text", text: direction === "high" ? "Nenhum fator positivo relevante." : "Nenhum fator negativo relevante." });
  }
  blocks.push({
    type: "text",
    text: `Qual desses pontos você considera ${direction === "high" ? "supervalorizado" : "subvalorizado"}? Ao registrar, você pode sugerir a nota que acha justa.`,
  });
  return blocks;
};

const replyExcerpt = (index: AnalysisIndex, node: AnalysisNode): AnswerBlock[] => {
  const evidences =
    node.kind === "evidence"
      ? [node]
      : [...index.values()].filter((n): n is EvidenceNode => n.kind === "evidence" && n.id.startsWith(`${node.id}.`));
  return [
    { type: "text", text: "Estes são os trechos em que me apoiei. Pode ter havido erro de leitura (tabela, página digitalizada, trecho fora de contexto):" },
    {
      type: "list",
      items: evidences.slice(0, 5).map((e) =>
        e.evidence.projectExcerpt
          ? `${e.number}: “${e.evidence.projectExcerpt.excerpt}” (${e.evidence.projectExcerpt.fileName ?? "texto livre"}${e.evidence.projectExcerpt.page !== undefined ? `, p. ${e.evidence.projectExcerpt.page}` : ""})`
          : `${e.number}: sem trecho (ausência de informação)`,
      ),
    },
    { type: "text", text: "Indique o trecho correto (arquivo e página) no argumento da contestação." },
  ];
};

const replyMissing = (node: AnalysisNode): AnswerBlock[] => [
  {
    type: "text",
    text: `Hoje ${nodeLabel(node)} se apoia em ${node.childIds.length || "nenhum"} ${node.kind === "criterion" ? "regra(s)" : "evidência(s)"}. Posso não ter encontrado algo no material.`,
  },
  {
    type: "text",
    text: "Descreva o que faltou e onde está (arquivo e página). Uma evidência nova entra numa reanálise; a contestação registra o seu ponto até lá.",
  },
];

export const debateReply = (message: string, context: AssistantContext): AssistantAnswer => {
  const index = indexAnalysis(context.analysis);
  const node = context.debateNodeId ? index.get(context.debateNodeId) : undefined;
  if (!node) {
    return { blocks: [{ type: "text", text: "Não encontrei o item em debate." }], sources: [], suggestions: [] };
  }
  const reason = detectReason(message, node.kind);

  const replies: Record<ContestationReason, () => AnswerBlock[]> = {
    polarity: () => replyPolarity(context, node),
    score_too_high: () => replyScore(index, node, "high"),
    score_too_low: () => replyScore(index, node, "low"),
    wrong_excerpt: () => replyExcerpt(index, node),
    missing_evidence: () => replyMissing(node),
    other: () => [
      { type: "text", text: "Entendi. Para registrar seu ponto com rastreabilidade, relembro a base da minha leitura:" },
      ...basisBlocks(index, node),
    ],
  };

  return {
    blocks: [
      ...replies[reason](),
      {
        type: "text",
        text: "Não altero a nota sozinho: se você mantém a discordância, registre a contestação. Ela fica na trilha de decisão.",
      },
    ],
    sources: [source(node)],
    suggestions: reasonChips(node).filter((chip) => chip !== CONTESTATION_REASON_LABELS[reason]),
    actions: recordAction(node, reason),
  };
};
