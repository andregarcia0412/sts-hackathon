/*
 * Project documents: accepted formats and the type the system recognizes from
 * the file name (MOCK: the real recognition also reads the content).
 * Testimonies weigh less as evidence and are checked against the records.
 */

export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".json"] as const;

export const MAX_FILE_BYTES = 20 * 1024 * 1024;

/** First match wins: [pattern on the file name (path included), type] */
const KIND_PATTERNS: [RegExp, string][] = [
  [/dossi[eê]/i, "Dossiê"],
  [/transcri|entrevista|depoimento/i, "Depoimento"],
  [/registro|relat[oó]rio|laborat[oó]rio|notas/i, "Registro técnico"],
  [/medi[cç](ao|ão|oes|ões)|medidas/i, "Medições"],
  [/cronograma|marcos|timeline/i, "Cronograma"],
  [/or[cç]amento|custos/i, "Orçamento"],
  [/m[eé]todo|metodologia|protocolo/i, "Método"],
  [/config/i, "Configuração"],
  [/resultado/i, "Resultados"],
  [/observa[cç]/i, "Observações"],
  [/invent[aá]rio/i, "Inventário"],
  [/revis[aã]o/i, "Revisão técnica"],
  [/plano|memorial|proposta/i, "Plano do projeto"],
];

const KIND_BY_EXTENSION: Record<string, string> = {
  ".csv": "Dados tabulares",
  ".xlsx": "Planilha",
  ".json": "Dados estruturados",
  ".md": "Nota técnica",
  ".txt": "Texto",
};

export const extensionOf = (fileName: string) => {
  const dot = fileName.lastIndexOf(".");
  return dot >= 0 ? fileName.slice(dot).toLowerCase() : "";
};

export const isAcceptedFile = (fileName: string) =>
  (ACCEPTED_EXTENSIONS as readonly string[]).includes(extensionOf(fileName));

export const recognizeDocumentKind = (fileName: string): string =>
  KIND_PATTERNS.find(([pattern]) => pattern.test(fileName))?.[1] ??
  KIND_BY_EXTENSION[extensionOf(fileName)] ??
  "Documento";
