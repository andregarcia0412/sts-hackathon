import type { Analysis } from "@/domain/types";

/* Contract of the analysis assistant (chatbot). Provisional, like domain/types.ts */

export type AssistantScreen = "analysis" | "decision";

/** What the assistant knows about the screen the analyst is looking at */
export interface AssistantContext {
  screen: AssistantScreen;
  analysis: Analysis;
  selectedNodeId: string | null;
}

export type AnswerBlock =
  | { type: "text"; text: string }
  | { type: "list"; items: string[] }
  | { type: "quote"; text: string; caption: string };

/** Link from an answer back to the node it is based on (traceability) */
export interface AnswerSource {
  nodeId: string;
  label: string;
}

export interface AssistantAnswer {
  blocks: AnswerBlock[];
  sources: AnswerSource[];
  /** Follow-up questions offered as chips */
  suggestions: string[];
}

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; answer: AssistantAnswer }
  | { id: string; role: "error"; text: string };
