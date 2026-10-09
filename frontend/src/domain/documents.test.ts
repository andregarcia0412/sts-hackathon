import { describe, expect, it } from "vitest";
import { isAcceptedFile, recognizeDocumentKind } from "@/domain/documents";

describe("recognizeDocumentKind", () => {
  it("recognizes the type from the name", () => {
    expect(recognizeDocumentKind("dossie_projeto.pdf")).toBe("Dossiê");
    expect(recognizeDocumentKind("registro_tecnico.pdf")).toBe("Registro técnico");
    expect(recognizeDocumentKind("transcricao_entrevista_tecnica.pdf")).toBe("Depoimento");
    expect(recognizeDocumentKind("evidencias/medicoes.csv")).toBe("Medições");
  });

  it("falls back to the extension, then to a generic type", () => {
    expect(recognizeDocumentKind("dados.xlsx")).toBe("Planilha");
    expect(recognizeDocumentKind("anexo.pdf")).toBe("Documento");
  });
});

describe("isAcceptedFile", () => {
  it("accepts the formats of the design", () => {
    for (const name of ["a.pdf", "a.DOCX", "a.txt", "a.md", "a.csv", "a.xlsx", "a.json"]) {
      expect(isAcceptedFile(name)).toBe(true);
    }
    expect(isAcceptedFile("foto.png")).toBe(false);
  });
});
