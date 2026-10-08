import { createContext, useContext, useEffect } from "react";
import type { AssistantContext, ChatMessage } from "@/domain/assistant";

export interface AssistantState {
  open: boolean;
  setOpen: (open: boolean) => void;
  messages: ChatMessage[];
  pending: boolean;
  send: (question: string) => void;
  clear: () => void;
  /** Context registered by the current screen (null on screens without it) */
  pageContext: AssistantContext | null;
  setPageContext: (context: AssistantContext | null) => void;
}

export const AssistantStateContext = createContext<AssistantState | null>(null);

export const useAssistant = () => {
  const state = useContext(AssistantStateContext);
  if (!state) throw new Error("useAssistant must be used inside AssistantProvider");
  return state;
};

/** Screens call this so the assistant knows what the analyst is looking at */
export const useRegisterAssistantContext = (context: AssistantContext) => {
  const { setPageContext } = useAssistant();
  const { screen, analysis, selectedNodeId } = context;

  useEffect(() => {
    setPageContext({ screen, analysis, selectedNodeId });
  }, [setPageContext, screen, analysis, selectedNodeId]);

  useEffect(() => () => setPageContext(null), [setPageContext]);
};
