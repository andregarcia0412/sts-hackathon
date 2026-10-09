import type { Evidence } from "@/domain/types";

/** Where an evidence comes from: a project document, the free text, or the web */
export type EvidenceSourceKind = "document" | "text" | "web" | "none";

export interface EvidenceSource {
  kind: EvidenceSourceKind;
  /** "Plano_de_Projeto.pdf, p. 4", "Descrição do projeto", "Manual de Frascati §2.18" */
  label: string;
}

export const evidenceSource = (evidence: Evidence): EvidenceSource => {
  const excerpt = evidence.projectExcerpt;
  if (excerpt?.fileName) {
    return {
      kind: "document",
      label: excerpt.page !== undefined ? `${excerpt.fileName}, p. ${excerpt.page}` : excerpt.fileName,
    };
  }
  if (excerpt) return { kind: "text", label: "Descrição em texto livre" };
  const web = evidence.references.find((r) => r.url);
  if (web) return { kind: "web", label: web.label };
  return { kind: "none", label: "Sem trecho associado" };
};
