import type { Framework } from "@/domain/types";

/*
 * Methods ("frameworks") that can generate an analysis tree. Each project may
 * have one analysis per method. Add a method here and the UI picks it up.
 */

export interface FrameworkInfo {
  /** Short label: breadcrumb root, tabs */
  label: string;
  /** Full name, used in documents */
  name: string;
  description: string;
  /** Whether every criterion must be met at the same time (true for Frascati) */
  allCriteriaRequired: boolean;
  /** Edition of the method and of our criteria set, recorded in the decision document */
  version: string;
  /** How the criteria combine, below the summary of the decision document */
  summaryNote: string;
}

export const FRAMEWORKS: Record<Framework, FrameworkInfo> = {
  frascati: {
    label: "Frascati",
    name: "Manual de Frascati (OCDE)",
    description:
      "Os 5 critérios que o MCTI usa como régua para P&D: novidade, criatividade, incerteza, sistematização e transferibilidade.",
    allCriteriaRequired: true,
    version: "Manual de Frascati 2015 · critérios v1.0",
    summaryNote:
      "Os cinco critérios são verificados em conjunto (Frascati 2015, §2.13): a leitura mais fraca puxa o resultado, sem média nem pesos. Todas as leituras são sugestões do sistema até a nota do analista.",
  },
  mcti_form: {
    label: "Formulário MCTI",
    name: "Formulário de P&D do MCTI (FORMP&D)",
    description:
      "Os campos do formulário que o avaliador do MCTI lê: elemento novo, barreira tecnológica, metodologia, descrição/escopo e cronograma.",
    allCriteriaRequired: false,
    version: "FORMP&D · critérios v1.0",
    summaryNote:
      "São os campos que o avaliador do MCTI lê no formulário; cada um é lido por si, sem média entre eles. Todas as leituras são sugestões do sistema até a nota do analista.",
  },
};

/** Display order of methods (the first one is the primary analysis) */
export const FRAMEWORK_ORDER: Framework[] = ["frascati", "mcti_form"];

export const sortByFramework = <T extends { framework: Framework }>(items: T[]) =>
  [...items].sort(
    (a, b) => FRAMEWORK_ORDER.indexOf(a.framework) - FRAMEWORK_ORDER.indexOf(b.framework),
  );
