import { describe, expect, it } from "vitest";
import type { AssistantAnswer, AssistantContext } from "@/domain/assistant";
import { soilSensorAnalysis } from "@/mocks/analysis-soil-sensor";
import { debateOpening, debateReply, detectReason } from "@/mocks/debateEngine";
import { withScoreExplanations } from "@/mocks/scoreExplanations";

const analysis = withScoreExplanations(soilSensorAnalysis);

const debating = (nodeId: string): AssistantContext => ({
  screen: "analysis",
  analysis,
  selectedNodeId: nodeId,
  debateNodeId: nodeId,
});

const allText = (answer: AssistantAnswer) =>
  answer.blocks
    .map((b) => (b.type === "list" ? b.items.join(" ") : b.text))
    .join(" ");

describe("detectReason", () => {
  it("maps chips and free text to a reason", () => {
    expect(detectReason("Polaridade errada (a favor × contra)", "evidence")).toBe("polarity");
    expect(detectReason("essa evidência deveria ser positiva", "evidence")).toBe("polarity");
    expect(detectReason("acho a nota alta demais", "rule")).toBe("score_too_high");
    expect(detectReason("foi rigoroso, está subestimado", "criterion")).toBe("score_too_low");
    expect(detectReason("o trecho não diz isso", "evidence")).toBe("wrong_excerpt");
    expect(detectReason("ignorou o relatório de 2026", "rule")).toBe("missing_evidence");
    expect(detectReason("não concordo", "rule")).toBe("other");
  });
});

describe("debateOpening", () => {
  it("states the basis and offers reasons that fit the node", () => {
    const answer = debateOpening(debating("crit-uncertainty.rule-proj-13.ev-3"), "crit-uncertainty.rule-proj-13.ev-3");

    expect(allText(answer)).toContain("Classifiquei como evidência negativa");
    expect(answer.suggestions).toContain("Polaridade errada (a favor × contra)");
    expect(answer.suggestions).not.toContain("Nota alta demais");
  });
});

describe("debateReply", () => {
  it("simulates flipping an evidence's polarity on its rule and criterion", () => {
    // 3.1.3 is negative (−8) in PROJ-13 (80); flipping gives +8 → 96.
    // PROJ-13 weighs 60% in Incerteza (72) → 72 + 0.6 × 16 = 81.6 ≈ 82
    const answer = debateReply(
      "Polaridade errada (a favor × contra)",
      debating("crit-uncertainty.rule-proj-13.ev-3"),
    );

    expect(allText(answer)).toContain("3.1 PROJ-13 Barreira tecnológica iria de 80 para 96");
    expect(allText(answer)).toContain("3 Incerteza iria de 72 para 82");
    expect(answer.actions).toEqual([
      { type: "record-contestation", nodeId: "crit-uncertainty.rule-proj-13.ev-3", reason: "polarity" },
    ]);
  });

  it("shows what pushes a score up when the analyst finds it too high", () => {
    const answer = debateReply("nota alta demais", debating("crit-uncertainty.rule-proj-13"));

    expect(allText(answer)).toContain("3.1.1 Hipótese de modelo descartada: +19");
    expect(allText(answer)).not.toContain("−8");
  });

  it("never changes the score by itself", () => {
    const answer = debateReply("não concordo", debating("crit-novelty"));

    expect(allText(answer)).toContain("Não altero a nota sozinho");
  });
});
