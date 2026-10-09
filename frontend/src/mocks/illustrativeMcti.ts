import type { Analysis, Criterion } from "@/domain/types";
import { soilSensorMctiAnalysis } from "@/mocks/analysis-soil-sensor-mcti";

/*
 * EXEMPLO ILUSTRATIVO: the back-end only produces the Frascati analysis. So
 * that the "Formulário MCTI" method keeps showing on real projects (as in the
 * mock), the front adds the fictitious MCTI tree of the demo, flagged as
 * `illustrative`: the screens say it is an example, and nothing recorded on it
 * (rule notes, triage, contestations, decision ids) is sent to the back-end.
 * The criterion scores follow the project's real Frascati reading, so the
 * example roughly tracks the project instead of always showing the same thing.
 */

const ID_SUFFIX = "-mcti-exemplo";

export const isIllustrativeAnalysisId = (analysisId: string) => analysisId.endsWith(ID_SUFFIX);

/** Frascati criterion (front or back-end key) whose score each MCTI field follows */
const FRASCATI_SOURCE: Record<string, string[]> = {
  novel_element: ["novelty"],
  technological_barrier: ["uncertainty"],
  methodology: ["systematic", "systematicity"],
  description_scope: ["creativity"],
  schedule: ["transferability", "reproducibility"],
};

const clamp = (value: number) => Math.min(100, Math.max(0, Math.round(value)));

const followScore = (template: Criterion, frascati: Analysis): Criterion => {
  const keys = FRASCATI_SOURCE[template.key] ?? [];
  const source = frascati.criteria.find((c) => keys.includes(c.key));
  // The back-end sends null when a criterion has no evidence: keep the example's score
  if (typeof source?.score !== "number") return structuredClone(template);
  const delta = source.score - template.score;
  return {
    ...structuredClone(template),
    score: clamp(source.score),
    rules: template.rules.map((rule) => ({ ...structuredClone(rule), score: clamp(rule.score + delta) })),
  };
};

export const illustrativeMcti = (frascati: Analysis): Analysis => ({
  ...structuredClone(soilSensorMctiAnalysis),
  id: `${frascati.id}${ID_SUFFIX}`,
  projectId: frascati.projectId,
  generatedAt: frascati.generatedAt,
  criteria: soilSensorMctiAnalysis.criteria.map((criterion) => followScore(criterion, frascati)),
  adjustments: [],
  illustrative: true,
});

/** Adds the example MCTI analysis when the back-end sent Frascati only */
export const withIllustrativeMcti = (analyses: Analysis[]): Analysis[] => {
  const frascati = analyses.find((a) => a.framework === "frascati");
  if (!frascati || analyses.some((a) => a.framework === "mcti_form")) return analyses;
  return [...analyses, illustrativeMcti(frascati)];
};
