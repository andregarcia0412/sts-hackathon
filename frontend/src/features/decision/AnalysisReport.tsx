import { FileText, Network, PenLine } from "lucide-react";
import { ReviewTag } from "@/components/ui/ReviewTag";
import type { ReviewMarker } from "@/domain/contestations";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { PolarityTag } from "@/components/ui/PolarityTag";
import { ReferenceLink } from "@/components/ui/ReferenceLink";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { APP_DISCLAIMER } from "@/config/app";
import { FRAMEWORKS } from "@/domain/frameworks";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";
import { indexAnalysis } from "@/domain/tree";
import type { AnalysisIndex } from "@/domain/tree";
import type { Analysis, Project } from "@/domain/types";
import { formatDateTime } from "@/lib/format";
import { breakdownFormula } from "@/lib/scoreFormat";
import { paths, reportAnchorId } from "@/routes/paths";

/*
 * Everything that is in the graph, as a readable/printable document.
 * Same numbering (1 / 1.1 / 1.1.1) as the analysis screen, so both can be
 * cross-checked; each item links back to its node in the graph.
 */

interface AnalysisReportProps {
  project: Project;
  analysis: Analysis;
}

export const ReportHeader = ({ project, analyses }: { project: Project; analyses: Analysis[] }) => (
  <header className="space-y-4">
    <div>
      <p className="font-sans text-xs font-semibold tracking-wide text-fg-muted uppercase">
        Análise preliminar de enquadramento · Lei do Bem (Lei nº 11.196/2005)
      </p>
      <h1 className="mt-1 text-3xl leading-tight font-semibold">{project.name}</h1>
    </div>
    <p className="rounded-md border border-score-moderate bg-score-moderate-soft px-4 py-3 font-sans text-sm">
      <strong>Documento de apoio à decisão.</strong> {APP_DISCLAIMER} As notas
      indicam a <strong>força da evidência</strong> encontrada no material, e
      não a probabilidade de aprovação.
    </p>
    <dl className="grid gap-x-6 gap-y-2 font-sans text-sm sm:grid-cols-[max-content_1fr]">
      <dt className="text-fg-muted">Empresa</dt>
      <dd>{project.company ?? "Não informada"}</dd>
      <dt className="text-fg-muted">Material analisado</dt>
      <dd>
        <ul>
          {project.documents.map((doc) => (
            <li key={doc.id} className="flex items-center gap-1.5">
              <FileText className="size-3.5 shrink-0 text-fg-muted" aria-hidden />
              {doc.fileName}
            </li>
          ))}
          {project.freeText && (
            <li className="flex items-center gap-1.5">
              <PenLine className="size-3.5 shrink-0 text-fg-muted" aria-hidden />
              Descrição em texto livre
            </li>
          )}
        </ul>
      </dd>
      <dt className="text-fg-muted">
        {analyses.length > 1 ? "Análises (uma por método)" : "Análise"}
      </dt>
      <dd>
        <ul className="space-y-1">
          {analyses.map((analysis) => (
            <li key={analysis.id}>
              {FRAMEWORKS[analysis.framework].name}
              <span className="block text-xs text-fg-muted">
                <span className="font-mono">{analysis.id}</span> · gerada em{" "}
                {formatDateTime(analysis.generatedAt)}
              </span>
            </li>
          ))}
        </ul>
      </dd>
    </dl>
  </header>
);

export const ReportSummary = ({ analysis }: { analysis: Analysis }) => (
  <section className="space-y-3">
    <h3 className="font-sans text-lg font-semibold">{FRAMEWORKS[analysis.framework].name}</h3>
    <table className="w-full border-collapse font-sans text-sm">
      <thead>
        <tr className="border-b border-border-strong text-left text-xs text-fg-muted uppercase">
          <th scope="col" className="py-2 pr-2 font-medium">#</th>
          <th scope="col" className="py-2 pr-2 font-medium">Critério</th>
          <th scope="col" className="py-2 pr-2 font-medium">Força da evidência</th>
          <th scope="col" className="py-2 font-medium">Faixa</th>
        </tr>
      </thead>
      <tbody>
        {analysis.criteria.map((criterion, i) => (
          <tr key={criterion.id} className="border-b border-border">
            <td className="py-2 pr-2 text-fg-muted tabular-nums">{i + 1}</td>
            <td className="py-2 pr-2 font-medium">{criterion.name}</td>
            <td className="py-2 pr-2">
              <ScoreBadge score={criterion.score} size="sm" />
            </td>
            <td className="py-2">{SCORE_BAND_LABELS[scoreBand(criterion.score)]}</td>
          </tr>
        ))}
      </tbody>
    </table>
    <p className="font-sans text-sm">
      <span className="text-fg-muted">Classificação sugerida pelo sistema: </span>
      {analysis.suggestedCategory
        ? SUGGESTED_CATEGORY_LABELS[analysis.suggestedCategory]
        : "não fornecida"}
    </p>
    <p className="text-sm text-fg-muted">
      {FRAMEWORKS[analysis.framework].allCriteriaRequired
        ? "Todos os critérios deste método precisam ser atendidos em conjunto. Uma nota baixa em qualquer um deles merece atenção na decisão."
        : FRAMEWORKS[analysis.framework].description}
    </p>
  </section>
);

export const ReportDetails = ({
  project,
  analysis,
  markers = new Map(),
}: AnalysisReportProps & { markers?: ReadonlyMap<string, ReviewMarker> }) => {
  const index = indexAnalysis(analysis);

  return (
    <ReportSection title={`Detalhamento · ${FRAMEWORKS[analysis.framework].label}`} id={`detalhamento-${analysis.framework}`}>
      {[...index.values()].map((node) => {
        if (node.kind !== "criterion") return null;
        const { criterion } = node;
        return (
          <section key={node.id} className="space-y-4 border-t border-border pt-4">
            <NodeHeading level={3} index={index} analysis={analysis} nodeId={node.id} projectId={project.id} review={markers.get(node.id)}>
              {node.number}. {criterion.name}
              <ScoreBadge score={criterion.score} showLabel size="sm" />
            </NodeHeading>
            <p>{criterion.summary}</p>
            {criterion.scoreExplanation && (
              <ScoreFormula
                text={breakdownFormula(criterion.scoreExplanation, criterion.score)}
                method={criterion.scoreExplanation.method}
              />
            )}
            {node.childIds.map((ruleId) => (
              <RuleBlock key={ruleId} index={index} analysis={analysis} ruleId={ruleId} projectId={project.id} markers={markers} />
            ))}
          </section>
        );
      })}
    </ReportSection>
  );
};

const RuleBlock = ({
  index,
  analysis,
  ruleId,
  projectId,
  markers,
}: {
  index: AnalysisIndex;
  analysis: Analysis;
  ruleId: string;
  projectId: string;
  markers: ReadonlyMap<string, ReviewMarker>;
}) => {
  const node = index.get(ruleId);
  if (node?.kind !== "rule") return null;
  const { rule } = node;

  return (
    <div className="space-y-3 pl-4">
      <NodeHeading level={4} index={index} analysis={analysis} nodeId={ruleId} projectId={projectId} review={markers.get(ruleId)}>
        {node.number} {rule.code} · {rule.name}
        <ScoreBadge score={rule.score} size="sm" />
      </NodeHeading>
      <p>{rule.explanation}</p>
      {rule.scoreExplanation && (
        <ScoreFormula
          text={breakdownFormula(rule.scoreExplanation, rule.score)}
          method={rule.scoreExplanation.method}
        />
      )}
      <div className="font-sans">
        <span className="text-xs text-fg-muted">Referência normativa: </span>
        <ReferenceLink reference={rule.normativeSource} />
      </div>
      <ol className="space-y-3">
        {node.childIds.map((evidenceId) => {
          const evidenceNode = index.get(evidenceId);
          if (evidenceNode?.kind !== "evidence") return null;
          const { evidence } = evidenceNode;
          return (
            <li
              key={evidenceId}
              className="space-y-2 rounded-md border border-border p-3 break-inside-avoid"
            >
              <NodeHeading level={5} index={index} analysis={analysis} nodeId={evidenceId} projectId={projectId} review={markers.get(evidenceId)}>
                {evidenceNode.number} {evidence.title}
                <PolarityTag polarity={evidence.polarity} />
              </NodeHeading>
              <p className="text-sm">{evidence.explanation}</p>
              {evidence.projectExcerpt ? (
                <blockquote className="border-l-2 border-border-strong pl-3 text-sm italic">
                  “{evidence.projectExcerpt.excerpt}”
                  <footer className="mt-1 font-sans text-xs text-fg-muted not-italic">
                    {evidence.projectExcerpt.fileName ?? "Descrição em texto livre"}
                    {evidence.projectExcerpt.page !== undefined &&
                      `, p. ${evidence.projectExcerpt.page}`}
                  </footer>
                </blockquote>
              ) : (
                <p className="font-sans text-xs text-fg-muted italic">
                  Sem trecho associado (ausência de informação no material).
                </p>
              )}
              {evidence.references.length > 0 && (
                <ul className="space-y-1 font-sans">
                  {evidence.references.map((reference) => (
                    <li key={reference.label}>
                      <ReferenceLink reference={reference} />
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
};

/** Compact, printable composition of a score */
const ScoreFormula = ({ text, method }: { text: string; method: string }) => (
  <p className="font-sans text-sm">
    <span className="text-fg-muted">Composição da nota (ilustrativa): </span>
    <span className="font-medium tabular-nums">{text}</span>
    <span className="block text-xs text-fg-muted">{method}</span>
  </p>
);

const HEADING_CLASSES = {
  3: "text-xl font-semibold",
  4: "text-base font-semibold",
  5: "text-sm font-semibold",
};

const NodeHeading = ({
  level,
  index,
  analysis,
  nodeId,
  projectId,
  review,
  children,
}: {
  level: 3 | 4 | 5;
  index: AnalysisIndex;
  analysis: Analysis;
  nodeId: string;
  projectId: string;
  /** Contested / revised / resolved (details in the trail) */
  review?: ReviewMarker;
  children: ReactNode;
}) => {
  const Tag = `h${level}` as const;
  const node = index.get(nodeId);
  return (
    <div className="flex items-start justify-between gap-3">
      <Tag
        id={reportAnchorId(analysis, nodeId)}
        className={`flex scroll-mt-20 flex-wrap items-center gap-2 rounded font-sans ${HEADING_CLASSES[level]}`}
      >
        {children}
        {review && <ReviewTag marker={review} />}
      </Tag>
      <Link
        to={paths.analysis(projectId, nodeId, analysis.framework)}
        className="btn-ghost shrink-0 px-1.5 py-0.5 text-xs print:hidden"
        aria-label={`Ver ${node?.number ?? ""} no grafo`}
      >
        <Network className="size-3.5" aria-hidden />
        Ver no grafo
      </Link>
    </div>
  );
};

/* Document sections are not numbered: 1 / 1.1 / 1.1.1 belongs to the analysis tree */
export const ReportSection = ({
  title,
  id,
  className = "",
  children,
}: {
  title: string;
  id?: string;
  className?: string;
  children: ReactNode;
}) => (
  <section id={id} className={`scroll-mt-16 space-y-4 ${className}`}>
    <h2 className="border-b-2 border-fg pb-1 font-sans text-2xl font-semibold">{title}</h2>
    {children}
  </section>
);
