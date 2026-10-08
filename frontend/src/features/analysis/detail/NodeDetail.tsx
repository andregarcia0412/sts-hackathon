import { FileText, MousePointerClick, PenLine } from "lucide-react";
import type { ReactNode } from "react";
import { PolarityTag } from "@/components/ui/PolarityTag";
import { ReferenceLink } from "@/components/ui/ReferenceLink";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { ScoreBreakdown } from "@/components/ui/ScoreBreakdown";
import { formatPoints } from "@/lib/scoreFormat";
import { POLARITY_ICONS, POLARITY_STYLES } from "@/components/ui/polarityStyles";
import type {
  AnalysisNode,
  CriterionNode,
  EvidenceNode,
  RuleNode,
} from "@/domain/tree";
import type { ProjectExcerpt } from "@/domain/types";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

/*
 * Full text of the selected node, always with sources and references.
 * Every score leads to its rule, the project excerpt and the norm within 1–2 clicks.
 */

interface NodeDetailProps {
  explorer: AnalysisExplorer;
}

export const NodeDetail = ({ explorer }: NodeDetailProps) => {
  const { selectedNode } = explorer;

  if (!selectedNode) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-sm text-fg-muted">
        <MousePointerClick className="size-6" aria-hidden />
        <p>
          Selecione um critério, regra ou evidência na árvore ou no grafo para
          ver o detalhe completo, com fontes e referências.
        </p>
      </div>
    );
  }

  return (
    <article
      aria-label="Detalhe do item selecionado"
      className="space-y-4 p-4 text-sm"
    >
      {selectedNode.kind === "criterion" && (
        <CriterionDetail node={selectedNode} explorer={explorer} />
      )}
      {selectedNode.kind === "rule" && (
        <RuleDetail node={selectedNode} explorer={explorer} />
      )}
      {selectedNode.kind === "evidence" && (
        <EvidenceDetail node={selectedNode} explorer={explorer} />
      )}
    </article>
  );
};

const KIND_LABELS: Record<AnalysisNode["kind"], string> = {
  criterion: "Critério",
  rule: "Regra",
  evidence: "Evidência",
};

const DetailHeader = ({
  node,
  title,
  badge,
}: {
  node: AnalysisNode;
  title: string;
  badge: ReactNode;
}) => (
  <header className="space-y-1.5">
    <p className="text-xs font-medium tracking-wide text-fg-muted uppercase">
      {KIND_LABELS[node.kind]} {node.number}
    </p>
    <h2 className="text-base leading-snug font-semibold">{title}</h2>
    <div>{badge}</div>
  </header>
);

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="space-y-1.5">
    <h3 className="text-xs font-semibold tracking-wide text-fg-muted uppercase">
      {title}
    </h3>
    {children}
  </section>
);

const ChildLink = ({
  number,
  onClick,
  children,
}: {
  number: string;
  onClick: () => void;
  children: ReactNode;
}) => (
  <li>
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-surface-muted"
    >
      <span className="shrink-0 text-xs text-fg-muted tabular-nums">{number}</span>
      {children}
    </button>
  </li>
);

const CriterionDetail = ({
  node,
  explorer,
}: {
  node: CriterionNode;
  explorer: AnalysisExplorer;
}) => (
  <>
    <DetailHeader
      node={node}
      title={node.criterion.name}
      badge={<ScoreBadge score={node.criterion.score} showLabel />}
    />
    <Section title="Por que esta nota">
      <p className="leading-relaxed">{node.criterion.summary}</p>
    </Section>
    <ScoreSection node={node} explorer={explorer} />
    <Section title="Regras que compõem o critério">
      <ul className="-mx-2">
        {node.childIds.map((id) => {
          const child = explorer.index.get(id);
          if (child?.kind !== "rule") return null;
          return (
            <ChildLink key={id} number={child.number} onClick={() => explorer.activate(id)}>
              <span className="min-w-0 flex-1">
                <span className="font-medium">{child.rule.code}</span>{" "}
                {child.rule.name}
              </span>
              <ScoreBadge score={child.rule.score} size="sm" />
            </ChildLink>
          );
        })}
      </ul>
    </Section>
  </>
);

const RuleDetail = ({
  node,
  explorer,
}: {
  node: RuleNode;
  explorer: AnalysisExplorer;
}) => (
  <>
    <DetailHeader
      node={node}
      title={`${node.rule.code} · ${node.rule.name}`}
      badge={<ScoreBadge score={node.rule.score} showLabel />}
    />
    <Section title="Explicação">
      <p className="leading-relaxed">{node.rule.explanation}</p>
    </Section>
    <ScoreSection node={node} explorer={explorer} />
    <Section title="Referência normativa">
      <ReferenceLink reference={node.rule.normativeSource} />
    </Section>
    <Section title="Evidências">
      <ul className="-mx-2">
        {node.childIds.map((id) => {
          const child = explorer.index.get(id);
          if (child?.kind !== "evidence") return null;
          const { polarity } = child.evidence;
          const Icon = POLARITY_ICONS[polarity];
          return (
            <ChildLink key={id} number={child.number} onClick={() => explorer.activate(id)}>
              <Icon
                className={`size-4 shrink-0 ${POLARITY_STYLES[polarity].text}`}
                aria-hidden
              />
              <span className="min-w-0 flex-1">{child.evidence.title}</span>
              <span className="sr-only">
                ({polarity === "positive" ? "positiva" : "negativa"})
              </span>
            </ChildLink>
          );
        })}
      </ul>
    </Section>
    <ParentNote explorer={explorer} parentId={node.parentId} />
  </>
);

const EvidenceDetail = ({
  node,
  explorer,
}: {
  node: EvidenceNode;
  explorer: AnalysisExplorer;
}) => (
  <>
    <DetailHeader
      node={node}
      title={node.evidence.title}
      badge={<PolarityTag polarity={node.evidence.polarity} />}
    />
    <Section title="Por que conta a favor ou contra">
      <p className="leading-relaxed">{node.evidence.explanation}</p>
    </Section>
    <EvidenceImpact node={node} explorer={explorer} />
    <Section title="Trecho do material do projeto">
      {node.evidence.projectExcerpt ? (
        <Excerpt excerpt={node.evidence.projectExcerpt} />
      ) : (
        <p className="text-fg-muted italic">
          Nenhum trecho associado: a evidência aponta a ausência de informação
          no material enviado.
        </p>
      )}
    </Section>
    <Section title="Referências">
      {node.evidence.references.length > 0 ? (
        <ul className="space-y-2">
          {node.evidence.references.map((reference) => (
            <li key={reference.label}>
              <ReferenceLink reference={reference} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-fg-muted">Sem referências.</p>
      )}
    </Section>
    <ParentNote explorer={explorer} parentId={node.parentId} />
  </>
);

const Excerpt = ({ excerpt }: { excerpt: ProjectExcerpt }) => (
  <figure className="rounded-md border border-border bg-surface-muted p-3">
    <blockquote className="leading-relaxed">“{excerpt.excerpt}”</blockquote>
    <figcaption className="mt-2 flex items-center gap-1.5 text-xs text-fg-muted">
      {excerpt.fileName ? (
        <>
          <FileText className="size-3.5" aria-hidden />
          {excerpt.fileName}
          {excerpt.page !== undefined && `, p. ${excerpt.page}`}
        </>
      ) : (
        <>
          <PenLine className="size-3.5" aria-hidden />
          Descrição em texto livre do projeto
        </>
      )}
    </figcaption>
  </figure>
);

const ParentNote = ({
  explorer,
  parentId,
}: {
  explorer: AnalysisExplorer;
  parentId?: string;
}) => {
  const parent = parentId ? explorer.index.get(parentId) : undefined;
  if (!parent) return null;
  const label =
    parent.kind === "criterion"
      ? `critério ${parent.number} ${parent.criterion.name}`
      : parent.kind === "rule"
        ? `regra ${parent.number} ${parent.rule.code}`
        : "";

  return (
    <p className="border-t border-border pt-3 text-xs text-fg-muted">
      Faz parte da{" "}
      <button
        type="button"
        className="font-medium text-accent hover:underline"
        onClick={() => explorer.select(parent.id)}
      >
        {label}
      </button>
    </p>
  );
};

/** Visual, step-by-step composition of a criterion or rule score */
const ScoreSection = ({
  node,
  explorer,
}: {
  node: CriterionNode | RuleNode;
  explorer: AnalysisExplorer;
}) => {
  const target = node.kind === "criterion" ? node.criterion : node.rule;
  if (!target.scoreExplanation) return null;

  const factors = target.scoreExplanation.factors.map((factor) => {
    const childId = factor.refId ? `${node.id}.${factor.refId}` : undefined;
    const child = childId ? explorer.index.get(childId) : undefined;
    return {
      ...factor,
      number: child?.number,
      onSelect: child ? () => explorer.activate(child.id) : undefined,
    };
  });

  return (
    <Section title="Como a nota foi formada">
      <ScoreBreakdown
        explanation={target.scoreExplanation}
        factors={factors}
        score={target.score}
        subject={node.kind === "criterion" ? "do critério" : "da regra"}
      />
    </Section>
  );
};

/** How many points this evidence moved its rule's score */
const EvidenceImpact = ({
  node,
  explorer,
}: {
  node: EvidenceNode;
  explorer: AnalysisExplorer;
}) => {
  const factor = node.rule.scoreExplanation?.factors.find(
    (f) => f.kind === "evidence" && f.refId === node.evidence.id,
  );
  if (!factor || !node.parentId) return null;
  const rule = explorer.index.get(node.parentId);

  return (
    <Section title="Impacto na nota">
      <p className="leading-relaxed">
        Esta evidência{" "}
        <strong className="tabular-nums">
          {factor.points >= 0 ? "soma" : "tira"} {formatPoints(factor.points).replace(/^[+−]/, "")}{" "}
          {Math.abs(factor.points) === 1 ? "ponto" : "pontos"}
        </strong>{" "}
        da nota da{" "}
        <button
          type="button"
          className="font-medium text-accent hover:underline"
          onClick={() => node.parentId && explorer.select(node.parentId)}
        >
          regra {rule?.number} {node.rule.code}
        </button>{" "}
        ({node.rule.score}/100).
      </p>
    </Section>
  );
};
