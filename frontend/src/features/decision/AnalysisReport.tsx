import { FileText, Network, PenLine } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { PolarityTag } from "@/components/ui/PolarityTag";
import { ReferenceLink } from "@/components/ui/ReferenceLink";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { APP_DISCLAIMER } from "@/config/app";
import { FRAMEWORK_LABELS, SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";
import { indexAnalysis } from "@/domain/tree";
import type { AnalysisIndex } from "@/domain/tree";
import type { Analysis, Project } from "@/domain/types";
import { formatDateTime } from "@/lib/format";
import { paths } from "@/routes/paths";

/*
 * Everything that is in the graph, as a readable/printable document.
 * Same numbering (1 / 1.1 / 1.1.1) as the analysis screen, so both can be
 * cross-checked; each item links back to its node in the graph.
 */

interface AnalysisReportProps {
  project: Project;
  analysis: Analysis;
}

export const ReportHeader = ({ project, analysis }: AnalysisReportProps) => (
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
      <dt className="text-fg-muted">Data da análise</dt>
      <dd>{formatDateTime(analysis.generatedAt)}</dd>
      <dt className="text-fg-muted">Identificador da análise</dt>
      <dd className="font-mono text-xs leading-5">{analysis.id}</dd>
      <dt className="text-fg-muted">Critérios usados</dt>
      <dd>Manual de {FRAMEWORK_LABELS[analysis.framework]} (5 critérios, MCTI)</dd>
    </dl>
  </header>
);

export const ReportSummary = ({ analysis }: { analysis: Analysis }) => (
  <ReportSection title="Resumo">
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
      Os cinco critérios precisam ser atendidos em conjunto. Uma nota baixa em
      qualquer um deles merece atenção na decisão.
    </p>
  </ReportSection>
);

export const ReportDetails = ({ project, analysis }: AnalysisReportProps) => {
  const index = indexAnalysis(analysis);

  return (
    <ReportSection title="Detalhamento por critério">
      {[...index.values()].map((node) => {
        if (node.kind !== "criterion") return null;
        const { criterion } = node;
        return (
          <section key={node.id} className="space-y-4 border-t border-border pt-4">
            <NodeHeading level={3} index={index} nodeId={node.id} projectId={project.id}>
              {node.number}. {criterion.name}
              <ScoreBadge score={criterion.score} showLabel size="sm" />
            </NodeHeading>
            <p>{criterion.summary}</p>
            {node.childIds.map((ruleId) => (
              <RuleBlock key={ruleId} index={index} ruleId={ruleId} projectId={project.id} />
            ))}
          </section>
        );
      })}
    </ReportSection>
  );
};

const RuleBlock = ({
  index,
  ruleId,
  projectId,
}: {
  index: AnalysisIndex;
  ruleId: string;
  projectId: string;
}) => {
  const node = index.get(ruleId);
  if (node?.kind !== "rule") return null;
  const { rule } = node;

  return (
    <div className="space-y-3 pl-4">
      <NodeHeading level={4} index={index} nodeId={ruleId} projectId={projectId}>
        {node.number} {rule.code} · {rule.name}
        <ScoreBadge score={rule.score} size="sm" />
      </NodeHeading>
      <p>{rule.explanation}</p>
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
              <NodeHeading level={5} index={index} nodeId={evidenceId} projectId={projectId}>
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

const HEADING_CLASSES = {
  3: "text-xl font-semibold",
  4: "text-base font-semibold",
  5: "text-sm font-semibold",
};

const NodeHeading = ({
  level,
  index,
  nodeId,
  projectId,
  children,
}: {
  level: 3 | 4 | 5;
  index: AnalysisIndex;
  nodeId: string;
  projectId: string;
  children: ReactNode;
}) => {
  const Tag = `h${level}` as const;
  const node = index.get(nodeId);
  return (
    <div className="flex items-start justify-between gap-3">
      <Tag
        id={`no-${nodeId}`}
        className={`flex scroll-mt-20 flex-wrap items-center gap-2 rounded font-sans ${HEADING_CLASSES[level]}`}
      >
        {children}
      </Tag>
      <Link
        to={paths.analysis(projectId, nodeId)}
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
  className = "",
  children,
}: {
  title: string;
  className?: string;
  children: ReactNode;
}) => (
  <section className={`space-y-4 ${className}`}>
    <h2 className="border-b-2 border-fg pb-1 font-sans text-2xl font-semibold">{title}</h2>
    {children}
  </section>
);
