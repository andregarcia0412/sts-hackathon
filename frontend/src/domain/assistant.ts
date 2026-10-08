import type { Analysis, ContestationReason } from "@/domain/types";

/* Contract of the analysis assistant (chatbot). Provisional, like domain/types.ts */

export type AssistantScreen = "analysis" | "decision";

/** What the assistant knows about the screen the analyst is looking at */
export interface AssistantContext {
  screen: AssistantScreen;
  analysis: Analysis;
  selectedNodeId: string | null;
  /** Set while the analyst is contesting a node (debate mode) */
  debateNodeId?: string | null;
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

/** Something the analyst can do from an answer, rendered as a button */
export type AssistantAction =
  | { type: "record-contestation"; nodeId: string; reason: ContestationReason }
  | { type: "request-reanalysis"; contestationId: string; nodeId: string };

export interface AssistantAnswer {
  blocks: AnswerBlock[];
  sources: AnswerSource[];
  /** Follow-up questions offered as chips */
  suggestions: string[];
  actions?: AssistantAction[];
}

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; answer: AssistantAnswer }
  | { id: string; role: "error"; text: string }
  /** Marker in the conversation, e.g. "Contestando 3.1 PROJ-13" */
  | { id: string; role: "event"; text: string };
