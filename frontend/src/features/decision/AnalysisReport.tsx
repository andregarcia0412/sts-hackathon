import { Plus } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import logoBnb from "@/assets/logo-bnb.svg";
import { ReviewTag } from "@/components/ui/ReviewTag";
import { Tag } from "@/components/ui/Tag";
import type { ReviewMarker } from "@/domain/contestations";
import { FRAMEWORKS } from "@/domain/frameworks";
import { SUGGESTED_CATEGORY_LABELS } from "@/domain/labels";
import {
  POLARITY_STATUS,
  RULE_RATING,
  RULE_STATUS,
  criterionStatus,
  criterionStatusInfo,
  ruleStatus,
} from "@/domain/qualitative";
import { projectCode } from "@/domain/projects";
import { PENDENCY_LABELS, evidenceTally, pendenciesIn, weakestCriterion } from "@/domain/report";
import type { Pendency, PendencyKind } from "@/domain/report";
import { indexAnalysis, ruleNodeId } from "@/domain/tree";
import type { AnalysisIndex, CriterionNode, RuleNode } from "@/domain/tree";
import type { Analysis, EvidenceReview, Project, RuleDecision } from "@/domain/types";
import type { OpenState } from "@/features/decision/reportState";
import { formatDate, formatDateTime, pluralize } from "@/lib/format";
import { paths, reportAnchorId } from "@/routes/paths";

/*
 * The analysis of one method as a readable/printable document (Figma "Tela de
 * documento"). Same numbering (1 / 1.1 / 1.1.1) as the evidence tree; criteria
 * and rules open like an accordion on screen and are all open on paper.
 */

/** Latest analyst review per node, for one analysis */
export interface AnalystReviews {
  decisions: ReadonlyMap<string, RuleDecision>;
  evidence: ReadonlyMap<string, EvidenceReview>;
}

/* ───────────────────────── Header ───────────────────────── */

export const ReportHeader = ({
  project,
  analysis,
  analyst,
}: {
  project: Project;
  analysis: Analysis;
  /** Who decided (or who is deciding) and the decision, if any */
  analyst: { name: string; note: string };
}) => {
  const framework = FRAMEWORKS[analysis.framework];
  const [methodName, criteriaVersion] = framework.version.split(" · ");
  const kinds = [...new Set(project.documents.map((d) => d.kind).filter(Boolean))] as string[];
  const material = [
    pluralize(project.documents.length, "arquivo", "arquivos"),
    project.freeText ? "descrição em texto livre" : "",
  ]
    .filter(Boolean)
    .join(" + ");

  return (
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
      <p className="max-w-3xl text-sm leading-6 text-fg-secondary">
        Documento de apoio à decisão. Não substitui o parecer oficial do MCTI. As leituras abaixo
        indicam o que o material sustenta e não a probabilidade de aprovação. Enquadramento técnico
        não equivale à fruição do benefício fiscal.
      </p>
      <dl className="grid gap-6 rounded-2xl bg-surface-sunken p-5 text-sm leading-5 sm:grid-cols-2 xl:grid-cols-4">
        <InfoColumn label="Projeto" value={`Projeto ${projectCode(project.id)} · ${project.company ?? "empresa não informada"}`}>
          {project.cutoffDate ? `Corte ${formatDate(project.cutoffDate)}` : `Enviado em ${formatDate(project.createdAt)}`}
        </InfoColumn>
        <InfoColumn label="Material analisado" value={material}>
          {kinds.length > 0 ? capitalize(kinds.map((k) => k.toLowerCase()).join(", ")) : "Tipos não reconhecidos"}
        </InfoColumn>
        <InfoColumn label="Método" value={methodName}>
          {capitalize(criteriaVersion ?? "")} · análise {analysis.id}
          {analysis.suggestedCategory && (
            <span className="block">Classificação sugerida: {SUGGESTED_CATEGORY_LABELS[analysis.suggestedCategory]}</span>
          )}
        </InfoColumn>
        <InfoColumn label="Analista" value={analyst.name}>
          {analyst.note}
        </InfoColumn>
      </dl>
    </header>
  );
};

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

const InfoColumn = ({ label, value, children }: { label: string; value: string; children: ReactNode }) => (
  <div className="flex min-w-0 flex-col gap-1">
    <dt className="caps-label text-fg-muted">{label}</dt>
    <dd className="flex flex-col gap-1">
      <span className="text-base leading-6 break-words">{value}</span>
      <span className="text-xs leading-[18px] text-fg-muted">{children}</span>
    </dd>
  </div>
);

/* ───────────────────────── Summary ───────────────────────── */

export const ReportSummary = ({
  analysis,
  reviews,
  pendencies,
  onOpen,
}: {
  analysis: Analysis;
  reviews: AnalystReviews;
  pendencies: Pendency[];
  onOpen: (nodeId: string) => void;
}) => {
  const weakest = weakestCriterion(analysis.criteria);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="w-full min-w-[40rem] border-collapse text-sm leading-5">
          <thead className="caps-label bg-surface-muted text-left text-fg-muted">
            <tr>
              <th scope="col" className="w-14 px-5 py-3.5 font-semibold">#</th>
              <th scope="col" className="px-3 py-3.5 font-semibold">Critério</th>
              <th scope="col" className="px-3 py-3.5 font-semibold">Leitura do sistema</th>
              <th scope="col" className="px-3 py-3.5 font-semibold">Notas do analista</th>
              <th scope="col" className="px-5 py-3.5 print:hidden">
                <span className="sr-only">Detalhe</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {analysis.criteria.map((criterion, i) => {
              const isWeakest = criterion.id === weakest?.id;
              const alerts = pendenciesIn(pendencies, criterion.id).length;
              const rated = criterion.rules.filter((r) => reviews.decisions.has(ruleNodeId(criterion, r))).length;
              return (
                <tr key={criterion.id} className={isWeakest ? "bg-state-attention-soft/60" : ""}>
                  <td className="px-5 py-3 text-fg-muted tabular-nums">{i + 1}</td>
                  <td className="px-3 py-3 font-semibold">{criterion.name}</td>
                  <td className="px-3 py-3">
                    {isWeakest ? (
                      <span className="font-medium text-state-attention-strong">
                        <span aria-hidden className="text-state-attention-mark">◆ </span>
                        {criterionStatusInfo(criterion).label} · mais fraca
                      </span>
                    ) : (
                      criterionStatusInfo(criterion).label
                    )}
                    {alerts > 0 && (
                      <span className="text-xs font-medium text-state-attention-strong">
                        {" "}· {pluralize(alerts, "alerta", "alertas")}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-fg-muted">
                    {rated} de {pluralize(criterion.rules.length, "regra", "regras")}
                  </td>
                  <td className="px-5 py-3 text-right print:hidden">
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => onOpen(criterion.id)}
                      aria-label={`Ver detalhe de ${criterion.name}`}
                    >
                      Ver detalhe
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs leading-[18px] text-fg-muted">{FRAMEWORKS[analysis.framework].summaryNote}</p>
    </div>
  );
};

/* ───────────────────────── Pendencies ───────────────────────── */

const PENDENCY_STYLES: Record<PendencyKind, { card: string; label: string; symbol: string }> = {
  divergence: { card: "bg-state-attention-soft", label: "text-state-attention-strong", symbol: "≠" },
  limit: { card: "bg-state-negative-soft", label: "text-accent", symbol: "−" },
  no_evidence: { card: "border-2 border-dashed border-border-strong bg-surface", label: "text-fg-soft", symbol: "?" },
  pending: { card: "border-2 border-dashed border-border-strong bg-surface", label: "text-fg-soft", symbol: "?" },
};

export const ReportPendencies = ({
  pendencies,
  onOpen,
}: {
  pendencies: Pendency[];
  onOpen: (nodeId: string) => void;
}) => {
  if (pendencies.length === 0) {
    return <p className="text-sm text-fg-muted">Nenhuma divergência, limite ou lacuna apontada pelo sistema.</p>;
  }
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {pendencies.map((pendency) => {
        const style = PENDENCY_STYLES[pendency.kind];
        return (
          <li key={`${pendency.kind}-${pendency.nodeId}-${pendency.text}`} className="flex break-inside-avoid">
            <button
              type="button"
              onClick={() => onOpen(pendency.nodeId)}
              className={`flex w-full flex-col gap-1.5 rounded-2xl px-4 py-3.5 text-left transition-[filter] hover:brightness-[0.98] ${style.card}`}
            >
              <span className={`caps-label ${style.label}`}>
                <span aria-hidden>{style.symbol} </span>
                {PENDENCY_LABELS[pendency.kind]} · {pendency.ref}
              </span>
              <span className="text-sm leading-5 text-fg">{pendency.text}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
};

/* ───────────────────────── Details (accordion) ───────────────────────── */

interface DetailsProps {
  project: Project;
  analysis: Analysis;
  markers?: ReadonlyMap<string, ReviewMarker>;
  reviews: AnalystReviews;
  open: OpenState;
  /** Criterion header (no parent) or rule row (parent = criterion) clicked */
  onToggle: (nodeId: string, parentId?: string) => void;
}

export const ReportDetails = ({ project, analysis, markers = new Map(), reviews, open, onToggle }: DetailsProps) => {
  const index = indexAnalysis(analysis);
  const weakest = weakestCriterion(analysis.criteria);

  return (
    <ol className="flex flex-col gap-3">
      {[...index.values()].map((node) =>
        node.kind === "criterion" ? (
          <CriterionItem
            key={node.id}
            node={node}
            index={index}
            project={project}
            analysis={analysis}
            markers={markers}
            reviews={reviews}
            open={open}
            onToggle={onToggle}
            weakest={node.id === weakest?.id}
          />
        ) : null,
      )}
    </ol>
  );
};

const CRITERION_READING_TEXT = {
  met: "text-fg-secondary",
  limited: "font-medium text-state-attention-strong",
  not_met: "font-medium text-state-negative",
};

const CriterionItem = ({
  node,
  index,
  project,
  analysis,
  markers,
  reviews,
  open,
  onToggle,
  weakest,
}: Omit<DetailsProps, "markers"> & {
  node: CriterionNode;
  index: AnalysisIndex;
  markers: ReadonlyMap<string, ReviewMarker>;
  weakest: boolean;
}) => {
  const { criterion } = node;
  const isOpen = open.criterionId === node.id;
  const status = criterionStatus(criterion);
  const reading = criterionStatusInfo(criterion).label;
  const bodyId = `${reportAnchorId(analysis, node.id)}-conteudo`;
  const review = markers.get(node.id);

  return (
    <li className="flex flex-col gap-4">
      <div
        id={reportAnchorId(analysis, node.id)}
        className={`flex scroll-mt-6 items-center gap-3 rounded-[28px] py-2 pr-5 pl-2 transition-colors print:border print:border-border print:bg-surface print:text-fg ${
          isOpen ? "bg-brand-deep text-white" : "border border-border bg-surface hover:bg-surface-muted"
        }`}
      >
        <h3 className="min-w-0 flex-1">
          <button
            type="button"
            aria-expanded={isOpen}
            aria-controls={bodyId}
            onClick={() => onToggle(node.id)}
            className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 text-left"
          >
            <span
              className={`flex size-10 shrink-0 items-center justify-center rounded-full text-base font-semibold ${
                isOpen ? "bg-brand-number" : "bg-surface-sunken text-fg"
              }`}
            >
              {node.number}
            </span>
            <span className="text-lg leading-6 font-semibold">{criterion.name}</span>
            {isOpen ? (
              <span className="text-xs leading-4 text-brand-blush print:text-fg-muted">
                {reading} · sugestão do sistema
              </span>
            ) : (
              <span className={`ml-auto text-sm leading-5 ${CRITERION_READING_TEXT[status]}`}>
                {(weakest || status !== "met") && <span aria-hidden>◆ </span>}
                {reading} · {pluralize(criterion.rules.length, "regra", "regras")}
              </span>
            )}
            {review && <ReviewTag marker={review} size="xs" />}
          </button>
        </h3>
        {isOpen ? (
          <TreeLink projectId={project.id} analysis={analysis} nodeId={node.id} number={node.number} inverted />
        ) : (
          <Plus className="size-5 shrink-0 print:hidden" aria-hidden />
        )}
      </div>

      <div id={bodyId} className={`flex flex-col gap-4 ${isOpen ? "" : "hidden print:flex"}`}>
        <p className="text-base leading-6">{criterion.summary}</p>
        <ul className="overflow-hidden rounded-2xl border border-border">
          {node.childIds.map((ruleId) => {
            const ruleNode = index.get(ruleId);
            return ruleNode?.kind === "rule" ? (
              <RuleItem
                key={ruleId}
                node={ruleNode}
                index={index}
                project={project}
                analysis={analysis}
                markers={markers}
                reviews={reviews}
                isOpen={open.ruleId === ruleId}
                onToggle={() => onToggle(ruleId, node.id)}
              />
            ) : null;
          })}
        </ul>
      </div>
    </li>
  );
};

const RULE_STATUS_TEXT = {
  sustained: "",
  partial: "text-state-attention-strong",
  contradictory: "text-state-attention-strong",
  not_sustained: "text-state-negative",
  no_evidence: "text-fg-soft",
};

const RuleItem = ({
  node,
  index,
  project,
  analysis,
  markers,
  reviews,
  isOpen,
  onToggle,
}: {
  node: RuleNode;
  index: AnalysisIndex;
  project: Project;
  analysis: Analysis;
  markers: ReadonlyMap<string, ReviewMarker>;
  reviews: AnalystReviews;
  isOpen: boolean;
  onToggle: () => void;
}) => {
  const { rule } = node;
  const status = ruleStatus(rule);
  const decision = reviews.decisions.get(node.id);
  const bodyId = `${reportAnchorId(analysis, node.id)}-conteudo`;
  const review = markers.get(node.id);

  return (
    <li
      id={reportAnchorId(analysis, node.id)}
      className={`scroll-mt-6 border-t border-border first:border-t-0 ${isOpen ? "bg-surface-muted" : ""} print:bg-surface`}
    >
      <h4>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={bodyId}
          onClick={onToggle}
          className="grid w-full gap-x-4 gap-y-1 px-5 py-3 text-left text-sm leading-5 transition-colors hover:bg-surface-muted sm:grid-cols-[2.5rem_minmax(0,1fr)_11rem_10rem]"
        >
          <span className={`tabular-nums ${isOpen ? "font-semibold text-action" : "text-fg-muted"}`}>{node.number}</span>
          <span className={isOpen ? "font-semibold" : ""}>
            {rule.name}
            {status !== "sustained" && (
              <span className={`font-semibold ${RULE_STATUS_TEXT[status]}`}> · {RULE_STATUS[status].short}</span>
            )}
            {review && (
              <>
                {" "}
                <ReviewTag marker={review} size="xs" />
              </>
            )}
          </span>
          <span className="text-fg-muted">{evidenceTally(rule)}</span>
          <span className="text-fg-muted">
            {decision ? (
              <>
                Nota: <strong className="font-semibold text-fg">{RULE_RATING[decision.rating].label}</strong>
              </>
            ) : (
              "Sem nota do analista"
            )}
          </span>
        </button>
      </h4>

      <div id={bodyId} className={`flex flex-col gap-4 px-5 pb-5 sm:pl-[4.75rem] ${isOpen ? "" : "hidden print:flex"}`}>
        <p className="text-base leading-6">{rule.explanation}</p>
        <p className="text-xs leading-4 text-fg-muted">
          <span className="caps-label">Referência normativa</span> ·{" "}
          {rule.normativeSource.url ? (
            <a href={rule.normativeSource.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
              {rule.normativeSource.label}
              <span className="sr-only"> (abre em nova aba)</span>
            </a>
          ) : (
            rule.normativeSource.label
          )}
          {" · "}
          {rule.code}
        </p>

        {decision && (
          <div className="flex flex-col gap-1.5 rounded-2xl border border-accent/30 bg-accent-soft p-4 text-sm leading-5">
            <p className="flex flex-wrap items-center gap-2">
              <span className="caps-label text-accent">Nota do analista</span>
              <Tag tone={RULE_RATING[decision.rating].tone} label={RULE_RATING[decision.rating].label} size="sm" />
              <span className="text-xs text-fg-muted">
                {decision.author} · {formatDateTime(decision.createdAt)}
              </span>
            </p>
            <p className="whitespace-pre-line">{decision.justification}</p>
          </div>
        )}

        {node.childIds.length > 0 && (
          <ol className="flex flex-col gap-3">
            {node.childIds.map((evidenceId) => (
              <EvidenceItem
                key={evidenceId}
                index={index}
                analysis={analysis}
                evidenceId={evidenceId}
                triage={reviews.evidence.get(evidenceId)}
                review={markers.get(evidenceId)}
              />
            ))}
          </ol>
        )}
        <TreeLink projectId={project.id} analysis={analysis} nodeId={node.id} number={node.number} />
      </div>
    </li>
  );
};

const EvidenceItem = ({
  index,
  analysis,
  evidenceId,
  triage,
  review,
}: {
  index: AnalysisIndex;
  analysis: Analysis;
  evidenceId: string;
  triage?: EvidenceReview;
  review?: ReviewMarker;
}) => {
  const node = index.get(evidenceId);
  if (node?.kind !== "evidence") return null;
  const { evidence } = node;
  const polarity = POLARITY_STATUS[evidence.polarity];
  const excerpt = evidence.projectExcerpt;
  const source = excerpt
    ? `${excerpt.fileName ?? "Descrição em texto livre"}${excerpt.page !== undefined ? `, p. ${excerpt.page}` : ""}`
    : "Sem trecho associado (ausência de informação no material)";

  return (
    <li
      id={reportAnchorId(analysis, evidenceId)}
      className="flex scroll-mt-6 flex-col gap-2 rounded-2xl bg-surface p-4 shadow-card break-inside-avoid print:border print:border-border print:shadow-none"
    >
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <h5 className="flex min-w-0 items-start gap-2 text-base leading-6 font-semibold">
          <Tag tone={polarity.tone} label={`Evidência ${polarity.label.toLowerCase()}`} size="plain" iconOnly />
          <span className={triage?.verdict === "discarded" ? "text-fg-muted line-through" : ""}>
            {node.number} · {evidence.title}
          </span>
          {review && <ReviewTag marker={review} size="xs" />}
        </h5>
        <p className="text-xs leading-5 text-fg-muted">
          {triage ? (
            <>
              <span className={triage.verdict === "confirmed" ? "font-medium text-state-positive" : "font-medium"}>
                {triage.verdict === "confirmed" ? "Confirmada" : "Descartada"}
              </span>{" "}
              · {triage.author}, {formatDateTime(triage.createdAt)}
            </>
          ) : (
            "Sugerida · não confirmada"
          )}
        </p>
      </div>
      {excerpt && (
        <blockquote className="ml-7 border-l-2 border-border-strong pl-3 text-sm leading-5 text-fg-soft">
          “{excerpt.excerpt}”
        </blockquote>
      )}
      <p className="ml-7 text-xs leading-4 text-fg-muted">
        {source}
        {evidence.references.map((reference) => (
          <span key={reference.label}>
            {" · "}
            {reference.url ? (
              <a href={reference.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {reference.label}
                <span className="sr-only"> (abre em nova aba)</span>
              </a>
            ) : (
              reference.label
            )}
          </span>
        ))}
      </p>
      <p className="ml-7 text-sm leading-5">{evidence.explanation}</p>
      {triage?.note && <p className="ml-7 text-xs leading-4 text-fg-muted">Motivo do descarte: “{triage.note}”</p>}
    </li>
  );
};

const TreeLink = ({
  projectId,
  analysis,
  nodeId,
  number,
  inverted = false,
}: {
  projectId: string;
  analysis: Analysis;
  nodeId: string;
  number: string;
  inverted?: boolean;
}) => (
  <Link
    to={paths.analysis(projectId, nodeId, analysis.framework)}
    className={`shrink-0 text-xs leading-5 font-semibold whitespace-nowrap hover:underline print:hidden ${
      inverted ? "text-white" : "self-start text-accent"
    }`}
    aria-label={`Ver ${number} na árvore`}
  >
    Ver na árvore
  </Link>
);

/* Document sections are not numbered: 1 / 1.1 / 1.1.1 belongs to the analysis tree */
export const ReportSection = ({
  title,
  id,
  className = "",
  aside,
  children,
}: {
  title: string;
  id?: string;
  className?: string;
  aside?: ReactNode;
  children: ReactNode;
}) => (
  <section id={id} className={`flex scroll-mt-6 flex-col gap-4 ${className}`}>
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <h2 className="text-xl leading-7 font-semibold">{title}</h2>
      {aside}
    </div>
    {children}
  </section>
);
