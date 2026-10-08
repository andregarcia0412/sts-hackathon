import { useRef, useState } from "react";
import type { ReactNode } from "react";
import type {
  AssistantAnswer,
  AssistantContext,
  ChatMessage,
} from "@/domain/assistant";
import { getNodeTitle, indexAnalysis } from "@/domain/tree";
import { AssistantStateContext } from "@/features/assistant/assistantState";
import { askAssistant, openDebate } from "@/services/api";

let messageCounter = 0;
const nextId = () => `msg-${++messageCounter}`;

/**
 * Conversation state for one project. Mounted above the analysis and
 * decision routes, so the chat survives switching between them.
 * Debate mode pins the conversation to one contested node.
 */
export const AssistantProvider = ({ children }: { children: ReactNode }) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [pageContext, setPageContext] = useState<AssistantContext | null>(null);
  const [debateNodeId, setDebateNodeId] = useState<string | null>(null);
  // Answers that arrive after "clear" must not reappear
  const conversationRef = useRef(0);

  const append = (message: ChatMessage) =>
    setMessages((current) => [...current, message]);

  /** Appends the answer of a request, unless the chat was cleared meanwhile */
  const respond = (request: Promise<AssistantAnswer>) => {
    const conversation = conversationRef.current;
    setPending(true);
    request
      .then((answer) => {
        if (conversation === conversationRef.current) {
          append({ id: nextId(), role: "assistant", answer });
        }
      })
      .catch(() => {
        if (conversation === conversationRef.current) {
          append({
            id: nextId(),
            role: "error",
            text: "Não consegui responder agora. Tente novamente.",
          });
        }
      })
      .finally(() => {
        if (conversation === conversationRef.current) setPending(false);
      });
  };

  const send = (question: string) => {
    const text = question.trim();
    if (!text || pending || !pageContext) return;
    append({ id: nextId(), role: "user", text });
    respond(askAssistant(text, { ...pageContext, debateNodeId }));
  };

  const startDebate = (nodeId: string) => {
    if (!pageContext) return;
    const node = indexAnalysis(pageContext.analysis).get(nodeId);
    setOpen(true);
    setDebateNodeId(nodeId);
    append({
      id: nextId(),
      role: "event",
      text: `Contestando ${node ? `${node.number} ${getNodeTitle(node)}` : "item"}`,
    });
    respond(openDebate(nodeId, pageContext));
  };

  const endDebate = (note = "Fim da contestação") => {
    setDebateNodeId(null);
    append({ id: nextId(), role: "event", text: note });
  };

  const clear = () => {
    conversationRef.current += 1;
    setMessages([]);
    setPending(false);
    setDebateNodeId(null);
  };

  return (
    <AssistantStateContext
      value={{
        open,
        setOpen,
        messages,
        pending,
        send,
        clear,
        pageContext,
        setPageContext,
        debateNodeId,
        startDebate,
        endDebate,
      }}
    >
      {children}
    </AssistantStateContext>
  );
};
