import { useRef, useState } from "react";
import type { ReactNode } from "react";
import type { AssistantContext, ChatMessage } from "@/domain/assistant";
import { AssistantStateContext } from "@/features/assistant/assistantState";
import { askAssistant } from "@/services/api";

let messageCounter = 0;
const nextId = () => `msg-${++messageCounter}`;

/**
 * Conversation state for one project. Mounted above the analysis and
 * decision routes, so the chat survives switching between them.
 */
export const AssistantProvider = ({ children }: { children: ReactNode }) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [pageContext, setPageContext] = useState<AssistantContext | null>(null);
  // Answers that arrive after "clear" must not reappear
  const conversationRef = useRef(0);

  const send = (question: string) => {
    const text = question.trim();
    if (!text || pending || !pageContext) return;
    const conversation = conversationRef.current;
    setMessages((current) => [...current, { id: nextId(), role: "user", text }]);
    setPending(true);

    askAssistant(text, pageContext)
      .then((answer) => {
        if (conversation !== conversationRef.current) return;
        setMessages((current) => [...current, { id: nextId(), role: "assistant", answer }]);
      })
      .catch(() => {
        if (conversation !== conversationRef.current) return;
        setMessages((current) => [
          ...current,
          { id: nextId(), role: "error", text: "Não consegui responder agora. Tente novamente." },
        ]);
      })
      .finally(() => {
        if (conversation === conversationRef.current) setPending(false);
      });
  };

  const clear = () => {
    conversationRef.current += 1;
    setMessages([]);
    setPending(false);
  };

  return (
    <AssistantStateContext
      value={{ open, setOpen, messages, pending, send, clear, pageContext, setPageContext }}
    >
      {children}
    </AssistantStateContext>
  );
};
