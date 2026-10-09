import { FRAMEWORKS } from "@/domain/frameworks";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { criterionStatusInfo } from "@/domain/qualitative";
import type { Pendency } from "@/domain/report";
import type { Analysis, Criterion, Decision, Project } from "@/domain/types";
import { formatDateTime } from "@/lib/format";

/*
 * Decision as a spreadsheet: one line per project, in the schema of the
 * back-end's GET /analyses/{id}/report.csv (historicos_classificados.csv, 27
 * columns), plus who decided and when. UTF-8 with BOM and semicolons, so it
 * opens straight in a Brazilian Excel.
 */

const MIN_CRITERIA = 5;

const criterionColumns = (count: number) =>
  Array.from({ length: Math.max(MIN_CRITERIA, count) }, (_, i) =>
    ["criterio", "estado", "justificativa", "fonte"].map((field) => `${field}_${i + 1}`),
  ).flat();

export const decisionCsvColumns = (criteriaCount: number) => [
  "projeto_id",
  "titulo",
  "classificacao",
  "justificativa",
  "limite",
  "fontes_decisivas",
  "divergencia_depoimento",
  ...criterionColumns(criteriaCount),
  "metodo",
  "analista",
  "decidido_em",
];

const sourceOf = (criterion: Criterion) => {
  const evidences = criterion.rules.flatMap((r) => r.evidences);
  // Evidence in favour first, as the back-end ranks the decisive source
  const main = [...evidences.filter((e) => e.polarity === "positive"), ...evidences].find(
    (e) => e.projectExcerpt?.fileName,
  )?.projectExcerpt;
  if (!main?.fileName) return "";
  return main.page ? `${main.fileName}, p. ${main.page}` : main.fileName;
};

const decisiveFiles = (analysis: Analysis) => {
  const files = analysis.criteria
    .flatMap((c) => c.rules)
    .flatMap((r) => r.evidences)
    .filter((e) => e.polarity === "positive")
    .map((e) => e.projectExcerpt?.fileName)
    .filter((name): name is string => !!name);
  return [...new Set(files)];
};

export const decisionCsvRow = (
  project: Pick<Project, "id" | "name">,
  analysis: Analysis,
  decision: Decision | undefined,
  pendencies: Pendency[],
): Record<string, string> => {
  const row: Record<string, string> = {
    projeto_id: project.id,
    titulo: project.name,
    classificacao: decision ? DECISION_OUTCOME_LABELS[decision.outcome] : "",
    justificativa: decision?.justification ?? "",
    limite: pendencies
      .filter((p) => p.kind === "limit")
      .map((p) => `${p.ref}: ${p.text}`)
      .join(" | "),
    fontes_decisivas: decisiveFiles(analysis).join(" | "),
    divergencia_depoimento: pendencies
      .filter((p) => p.kind === "divergence")
      .map((p) => `${p.ref}: ${p.text}`)
      .join(" "),
    metodo: `${FRAMEWORKS[analysis.framework].name}${analysis.illustrative ? " (exemplo ilustrativo)" : ""}`,
    analista: decision?.analystName ?? "",
    decidido_em: decision ? formatDateTime(decision.decidedAt) : "",
  };
  analysis.criteria.forEach((criterion, i) => {
    const n = i + 1;
    row[`criterio_${n}`] = criterion.name;
    row[`estado_${n}`] = criterionStatusInfo(criterion).label;
    row[`justificativa_${n}`] = criterion.summary;
    row[`fonte_${n}`] = sourceOf(criterion);
  });
  return row;
};

/**
 * A cell starting with = + - @ would run as a formula in Excel: the text of
 * an uploaded document must never do that (CSV injection).
 */
const neutralize = (value: string) => (/^[=+\-@\t\r]/.test(value) ? `'${value}` : value);

const quote = (value: string) => {
  const safe = neutralize(value);
  return /[;"\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
};

export const toCsv = (columns: string[], rows: Record<string, string>[]): string =>
  "\uFEFF" +
  [columns, ...rows.map((row) => columns.map((column) => row[column] ?? ""))]
    .map((cells) => cells.map(quote).join(";"))
    .join("\r\n") +
  "\r\n";

/** "parecer_<projeto>_<método>.csv", like the back-end's file name */
export const decisionCsvFileName = (project: Pick<Project, "id">, analysis: Pick<Analysis, "framework">) =>
  `parecer_${project.id}_${analysis.framework}.csv`.replace(/[^\w.-]+/g, "_");
