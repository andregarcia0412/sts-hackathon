import { describe, expect, it } from "vitest";
import {
  answerQuestion,
  resolveTargetNode,
} from "@/mocks/assistantEngine";
import type {
  AssistantAnswer,
  AssistantContext,
} from "@/domain/assistant";
import { indexAnalysis } from "@/domain/tree";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";

const index = indexAnalysis(soilSensorAnalysis);

const context = (selectedNodeId: string | null = null): AssistantContext => ({
  screen: "analysis",
  analysis: soilSensorAnalysis,
  selectedNodeId,
});

const allText = (answer: AssistantAnswer) =>
  answer.blocks
    .map((b) => (b.type === "list" ? b.items.join(" ") : b.text))
    .join(" ");

describe("resolveTargetNode", () => {
  it("finds a node by its number", () => {
    expect(resolveTargetNode("e a evidência 3.1.2?", index, null)?.id).toBe(
      "crit-uncertainty.rule-proj-13.ev-2",
    );
  });

  it("finds a criterion by 'critério N' or by name, ignoring accents", () => {
    expect(resolveTargetNode("como foi o critério 4?", index, null)?.id).toBe(
      "crit-systematic",
    );
    expect(resolveTargetNode("nota de sistematizacao", index, null)?.id).toBe(
      "crit-systematic",
    );
  });

  it("finds a rule by code, preferring the selected criterion", () => {
    expect(
      resolveTargetNode("explique a PROJ-14", index, "crit-transferability")?.id,
    ).toBe("crit-transferability.rule-proj-14");
    expect(resolveTargetNode("explique a proj-14", index, null)?.id).toBe(
      "crit-uncertainty.rule-proj-14",
    );
  });

  it("falls back to the selected node", () => {
    expect(
      resolveTargetNode("como esse escore foi calculado?", index, "crit-novelty")
        ?.id,
    ).toBe("crit-novelty");
  });

  it("does not treat years or scores as node numbers", () => {
    expect(resolveTargetNode("em 2026 a nota 80 é boa?", index, null)).toBeUndefined();
  });
});

describe("answerQuestion", () => {
  it("explains a criterion score through its rules and cites them", () => {
    const answer = answerQuestion(
      "Como o escore desse critério foi calculado?",
      context("crit-uncertainty"),
    );

    expect(allText(answer)).toContain("72/100");
    expect(allText(answer)).toContain("PROJ-13");
    expect(answer.sources.map((s) => s.nodeId)).toEqual(
      expect.arrayContaining(["crit-uncertainty", "crit-uncertainty.rule-proj-13"]),
    );
  });

  it("explains how an evidence was formed, with the project excerpt", () => {
    const answer = answerQuestion(
      "Me explique melhor como essa evidência associada à essa regra foi formada",
      context("crit-uncertainty.rule-proj-13.ev-1"),
    );

    const quote = answer.blocks.find((b) => b.type === "quote");
    expect(quote).toMatchObject({
      caption: expect.stringContaining("Relatorio_Tecnico_2025_EXEMPLO.pdf, p. 4"),
    });
    expect(allText(answer)).toContain("PROJ-13");
    expect(answer.sources[0].nodeId).toBe("crit-uncertainty.rule-proj-13.ev-1");
  });

  it("never gives a verdict", () => {
    const answer = answerQuestion("Esse projeto vai ser aprovado?", context());
    const text = allText(answer).toLowerCase();

    expect(text).toContain("decisão é do analista");
    expect(text).not.toMatch(/\b(está|será|seria) (aprovado|reprovado)/);
  });

  it("lists the weakest criteria", () => {
    const answer = answerQuestion("Quais os pontos fracos?", context());

    expect(allText(answer)).toContain("Transferibilidade");
    expect(answer.sources[0].nodeId).toBe("crit-transferability");
  });

  it("asks for a target when the question needs one and nothing is selected", () => {
    const answer = answerQuestion("como foi calculada essa nota?", context());

    expect(allText(answer)).toMatch(/selecione|cite/i);
    expect(answer.suggestions.length).toBeGreaterThan(0);
  });
});
