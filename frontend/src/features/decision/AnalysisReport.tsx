import { PenLine, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import logoBnb from "@/assets/logo-bnb.svg";
import { ArticleIcon } from "@/components/icons/MaterialIcons";
import { ReferenceLink } from "@/components/ui/ReferenceLink";
import { ReviewTag } from "@/components/ui/ReviewTag";
import { Tag } from "@/components/ui/Tag";
import { APP_DISCLAIMER } from "@/config/app";
import type { ReviewMarker } from "@/domain/contestations";
import { FRAMEWORKS } from "@/domain/frameworks";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import {
  POLARITY_STATUS,
  RULE_RATING,
  RULE_STATUS,
  criterionStatusInfo,
  ruleStatus,
} from "@/domain/qualitative";
import { indexAnalysis, ruleNodeId } from "@/domain/tree";
import type { AnalysisIndex } from "@/domain/tree";
import type { Analysis, EvidenceReview, Project, RuleDecision } from "@/domain/types";
import { formatDateTime } from "@/lib/format";
import { breakdownFormula } from "@/lib/scoreFormat";
import { paths, reportAnchorId } from "@/routes/paths";

/*
 * Everything that is in the graph, as a readable/printable document.
 * Same numbering (1 / 1.1 / 1.1.1) as the analysis screen, so both can be
 * cross-checked; each item links back to its node in the graph. The analyst's
 * rule ratings and evidence triage appear next to what they refer to.
 */

/** Latest analyst review per node, for one analysis */
export interface AnalystReviews {
  decisions: ReadonlyMap<string, RuleDecision>;
  evidence: ReadonlyMap<string, EvidenceReview>;
}

export const ReportHeader = ({ project, analyses }: { project: Project; analyses: Analysis[] }) => (
  <header className="flex flex-col gap-6">
    <div className="flex items-start justify-between gap-6">
      <div className="flex flex-col gap-2">
        <p className="caps-label text-accent">
          Análise preliminar de enquadramento · Lei do Bem (Lei nº 11.196/2005)
        </p>
        <h1 className="text-[28px] leading-9 font-semibold">{project.name}</h1>
      </div>
      <img src={logoBnb} alt="Banco do Nordeste" width={101} height={36} className="mt-1 shrink-0" />
    </div>
    <p className="flex items-start gap-3 rounded-xl bg-state-attention-soft px-4 py-3 text-sm leading-5 text-fg-soft">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-state-attention" strokeWidth={2.5} aria-hidden />
      <span>
        <strong className="font-semibold">Documento de apoio à decisão.</strong> {APP_DISCLAIMER} As
        notas indicam a <strong className="font-semibold">força da evidência</strong> encontrada no
        material, e não a probabilidade de aprovação.
      </span>
    </p>
    <dl className="grid gap-x-8 gap-y-3 text-sm leading-5 sm:grid-cols-[max-content_1fr]">
      <dt className="caps-label pt-0.5 text-fg-muted">Empresa</dt>
      <dd>{project.company ?? "Não informada"}</dd>
      <dt className="caps-label pt-0.5 text-fg-muted">Material analisado</dt>
      <dd>
        <ul className="flex flex-col gap-1">
          {project.documents.map((doc) => (
            <li key={doc.id} className="flex items-center gap-1.5">
              <ArticleIcon className="size-4 shrink-0 text-fg-secondary" />
              {doc.fileName}
            </li>
          ))}
          {project.freeText && (
            <li className="flex items-center gap-1.5">
              <PenLine className="size-4 shrink-0 text-fg-secondary" aria-hidden />
              Descrição em texto livre
            </li>
          )}
        </ul>
      </dd>
      <dt className="caps-label pt-0.5 text-fg-muted">
        {analyses.length > 1 ? "Análises (uma por método)" : "Análise"}
      </dt>
      <dd>
        <ul className="flex flex-col gap-1.5">
          {analyses.map((analysis) => (
            <li key={analysis.id}>
              {FRAMEWORKS[analysis.framework].name}
              <span className="block text-xs leading-4 text-fg-muted">
                {FRAMEWORKS[analysis.framework].version} ·{" "}
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

export const ReportSummary = ({ analysis, reviews }: { analysis: Analysis; reviews: AnalystReviews }) => (
  <section className="flex flex-col gap-3">
    <h3 className="text-lg leading-6 font-semibold">{FRAMEWORKS[analysis.framework].name}</h3>
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm leading-5">
        <thead className="caps-label bg-surface-muted text-left text-fg-muted">
          <tr>
            <th scope="col" className="px-3 py-2.5 font-semibold">#</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Critério</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Leitura do sistema</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Força da evidência</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Notas do analista</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {analysis.criteria.map((criterion, i) => {
            const status = criterionStatusInfo(criterion);
            const rated = criterion.rules.filter((r) =>
              reviews.decisions.has(ruleNodeId(criterion, r)),
            ).length;
            const complete = rated === criterion.rules.length && rated > 0;
            return (
              <tr key={criterion.id}>
                <td className="px-3 py-2.5 text-fg-muted tabular-nums">{i + 1}</td>
                <td className="px-3 py-2.5 font-semibold">{criterion.name}</td>
                <td className="px-3 py-2.5">
                  <Tag tone={status.tone} label={status.label} size="sm" />
                </td>
                <td className="px-3 py-2.5 tabular-nums">{criterion.score}/100</td>
                <td className="px-3 py-2.5">
                  <Tag
                    tone={complete ? "positive" : "neutral"}
                    label={`${rated} de ${criterion.rules.length} regras`}
                    size="sm"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    <p className="text-sm leading-5">
      <span className="text-fg-muted">Classificação sugerida pelo sistema: </span>
      {analysis.suggestedCategory
        ? SUGGESTED_CATEGORY_LABELS[analysis.suggestedCategory]
        : "não fornecida"}
    </p>
    <p className="text-sm leading-5 text-fg-muted">
      {FRAMEWORKS[analysis.framework].allCriteriaRequired
        ? "Todos os critérios deste método precisam ser atendidos em conjunto. Uma leitura fraca em qualquer um deles merece atenção na decisão."
        : FRAMEWORKS[analysis.framework].description}
    </p>
  </section>
);

export const ReportDetails = ({
  project,
  analysis,
  markers = new Map(),
  reviews,
}: {
  project: Project;
  analysis: Analysis;
  markers?: ReadonlyMap<string, ReviewMarker>;
  reviews: AnalystReviews;
}) => {
  const index = indexAnalysis(analysis);

  return (
    <ReportSection
      title={`Detalhamento · ${FRAMEWORKS[analysis.framework].label}`}
      id={`detalhamento-${analysis.framework}`}
    >
      {[...index.values()].map((node) => {
        if (node.kind !== "criterion") return null;
        const { criterion } = node;
        const status = criterionStatusInfo(criterion);
        return (
          <section key={node.id} className="flex flex-col gap-4 border-t border-border pt-6 first-of-type:border-t-0 first-of-type:pt-0">
            <NodeHeading
              level={3}
              analysis={analysis}
              index={index}
              nodeId={node.id}
              projectId={project.id}
              review={markers.get(node.id)}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-action text-sm font-bold text-white">
                {node.number}
              </span>
              {criterion.name}
              <Tag tone={status.tone} label={status.label} size="sm" />
            </NodeHeading>
            <p className="text-sm leading-6">{criterion.summary}</p>
            {criterion.scoreExplanation && (
              <ScoreFormula
                score={criterion.score}
                text={breakdownFormula(criterion.scoreExplanation, criterion.score)}
                method={criterion.scoreExplanation.method}
              />
            )}
            {node.childIds.map((ruleId) => (
              <RuleBlock
                key={ruleId}
                index={index}
                analysis={analysis}
                ruleId={ruleId}
                projectId={project.id}
                markers={markers}
                reviews={reviews}
              />
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
  reviews,
}: {
  index: AnalysisIndex;
  analysis: Analysis;
  ruleId: string;
  projectId: string;
  markers: ReadonlyMap<string, ReviewMarker>;
  reviews: AnalystReviews;
}) => {
  const node = index.get(ruleId);
  if (node?.kind !== "rule") return null;
  const { rule } = node;
  const status = RULE_STATUS[ruleStatus(rule)];
  const decision = reviews.decisions.get(ruleId);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface-muted p-4 break-inside-avoid-page">
      <NodeHeading
        level={4}
        analysis={analysis}
        index={index}
        nodeId={ruleId}
        projectId={projectId}
        review={markers.get(ruleId)}
      >
        <span className="text-accent tabular-nums">{node.number}</span>
        <span>
          {rule.name} <span className="font-normal text-fg-muted">· {rule.code}</span>
        </span>
        <Tag tone={status.tone} label={status.label} size="sm" />
      </NodeHeading>
      <p className="text-sm leading-6">{rule.explanation}</p>
      {rule.scoreExplanation && (
        <ScoreFormula
          score={rule.score}
          text={breakdownFormula(rule.scoreExplanation, rule.score)}
          method={rule.scoreExplanation.method}
        />
      )}
      <div className="text-sm">
        <span className="caps-label text-fg-muted">Referência normativa </span>
        <ReferenceLink reference={rule.normativeSource} />
      </div>

      {decision ? (
        <div className="flex flex-col gap-1.5 rounded-lg border border-accent/30 bg-accent-soft p-3 text-sm leading-5">
          <p className="flex flex-wrap items-center gap-2">
            <span className="caps-label text-accent">Nota do analista</span>
            <Tag tone={RULE_RATING[decision.rating].tone} label={RULE_RATING[decision.rating].label} size="sm" />
            <span className="text-xs text-fg-muted">
              {decision.author} · {formatDateTime(decision.createdAt)}
            </span>
          </p>
          <p className="whitespace-pre-line">{decision.justification}</p>
        </div>
      ) : (
        <p className="rounded-lg border border-dashed border-border-strong px-3 py-2 text-xs leading-4 text-fg-muted">
          Sem nota do analista para esta regra (a leitura acima é só a sugestão do sistema).
        </p>
      )}

      {node.childIds.length > 0 && (
        <ol className="flex flex-col gap-2">
          {node.childIds.map((evidenceId) => {
            const evidenceNode = index.get(evidenceId);
            if (evidenceNode?.kind !== "evidence") return null;
            const { evidence } = evidenceNode;
            const polarity = POLARITY_STATUS[evidence.polarity];
            const triage = reviews.evidence.get(evidenceId);
            return (
              <li
                key={evidenceId}
                className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-3 break-inside-avoid"
              >
                <NodeHeading
                  level={5}
                  analysis={analysis}
                  index={index}
                  nodeId={evidenceId}
                  projectId={projectId}
                  review={markers.get(evidenceId)}
                >
                  <span className="text-fg-muted tabular-nums">{evidenceNode.number}</span>
                  <span className={triage?.verdict === "discarded" ? "text-fg-muted line-through" : ""}>
                    {evidence.title}
                  </span>
                  <Tag tone={polarity.tone} label={polarity.label} size="sm" />
                </NodeHeading>
                <p className="text-sm leading-5">{evidence.explanation}</p>
                {evidence.projectExcerpt ? (
                  <blockquote className="border-l-2 border-action pl-3 text-sm leading-5 text-fg-soft">
                    “{evidence.projectExcerpt.excerpt}”
                    <footer className="mt-1 text-xs leading-4 text-fg-muted">
                      {evidence.projectExcerpt.fileName ?? "Descrição em texto livre"}
                      {evidence.projectExcerpt.page !== undefined &&
                        `, p. ${evidence.projectExcerpt.page}`}
                    </footer>
                  </blockquote>
                ) : (
                  <p className="text-xs leading-4 text-fg-muted italic">
                    Sem trecho associado (ausência de informação no material).
                  </p>
                )}
                {evidence.references.length > 0 && (
                  <ul className="flex flex-col gap-1">
                    {evidence.references.map((reference) => (
                      <li key={reference.label}>
                        <ReferenceLink reference={reference} />
                      </li>
                    ))}
                  </ul>
                )}
                <p className="text-xs leading-4 text-fg-muted">
                  {triage ? (
                    <>
                      <strong
                        className={`font-semibold ${triage.verdict === "confirmed" ? "text-state-positive" : "text-fg-secondary"}`}
                      >
                        {triage.verdict === "confirmed" ? "Confirmada" : "Descartada"} pelo analista
                      </strong>{" "}
                      · {triage.author}, {formatDateTime(triage.createdAt)}
                      {triage.note && ` · “${triage.note}”`}
                    </>
                  ) : (
                    "Sugerida pelo sistema · não confirmada pelo analista"
                  )}
                </p>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
};

/** Compact, printable composition of a score */
const ScoreFormula = ({ score, text, method }: { score: number; text: string; method: string }) => (
  <p className="text-sm leading-5">
    <span className="text-fg-muted">Força da evidência </span>
    <strong className="font-semibold tabular-nums">{score}/100</strong>
    <span className="text-fg-muted"> · composição (ilustrativa): </span>
    <span className="font-medium tabular-nums">{text}</span>
    <span className="block text-xs leading-4 text-fg-muted">{method}</span>
  </p>
);

const HEADING_CLASSES = {
  3: "text-lg leading-6 font-semibold",
  4: "text-base leading-5 font-semibold",
  5: "text-sm leading-5 font-semibold",
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
  const Heading = `h${level}` as const;
  const node = index.get(nodeId);
  return (
    <div className="flex items-start justify-between gap-3">
      <Heading
        id={reportAnchorId(analysis, nodeId)}
        className={`flex scroll-mt-6 flex-wrap items-center gap-2 ${HEADING_CLASSES[level]}`}
      >
        {children}
        {review && <ReviewTag marker={review} />}
      </Heading>
      <Link
        to={paths.analysis(projectId, nodeId, analysis.framework)}
        className="btn-link shrink-0 whitespace-nowrap print:hidden"
        aria-label={`Ver ${node?.number ?? ""} na árvore`}
      >
        Ver na árvore
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
  <section id={id} className={`flex scroll-mt-6 flex-col gap-5 ${className}`}>
    <h2 className="border-b border-border-strong pb-2 text-xl leading-7 font-semibold">{title}</h2>
    {children}
  </section>
);
