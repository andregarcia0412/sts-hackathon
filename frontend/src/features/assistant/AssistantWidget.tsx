import {
  Bot,
  Flag,
  MessageCircleQuestion,
  RotateCcw,
  SendHorizontal,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { AssistantAction, AssistantAnswer, ChatMessage } from "@/domain/assistant";
import { CONTESTATION_REASON_LABELS } from "@/domain/labels";
import type { ContestationReason } from "@/domain/types";
import { FRAMEWORKS } from "@/domain/frameworks";
import { getNodeTitle, indexAnalysis } from "@/domain/tree";
import { ContestationForm } from "@/features/assistant/ContestationForm";
import { useAssistant } from "@/features/assistant/assistantState";
import { starterSuggestions } from "@/mocks/assistantEngine";
import { paths, reportAnchorId } from "@/routes/paths";

const PANEL_ID = "analysis-assistant";

/**
 * Floating assistant (bottom-right) for the analysis and decision screens.
 * Answers explain scores and evidences, never give a verdict, and link back
 * to the nodes they are based on. In debate mode the analyst contests a node.
 */
export const AssistantWidget = () => {
  const { open, setOpen, pageContext } = useAssistant();
  const launcherRef = useRef<HTMLButtonElement>(null);

  // Only screens that registered a context (analysis/decision with data) get the bot
  if (!pageContext) return null;

  const close = () => {
    setOpen(false);
    launcherRef.current?.focus();
  };

  return (
    <div className="print:hidden">
      {open && <AssistantPanel onClose={close} />}
      <button
        ref={launcherRef}
        type="button"
        aria-expanded={open}
        aria-controls={PANEL_ID}
        aria-label={open ? "Fechar assistente" : "Abrir assistente da análise"}
        onClick={() => (open ? close() : setOpen(true))}
        className="fixed right-4 bottom-4 z-40 flex size-14 items-center justify-center rounded-full bg-accent text-accent-fg shadow-lg transition-transform hover:scale-105"
      >
        {open ? (
          <X className="size-6" aria-hidden />
        ) : (
          <MessageCircleQuestion className="size-6" aria-hidden />
        )}
      </button>
    </div>
  );
};

type Recording = Extract<AssistantAction, { type: "record-contestation" }>;

const AssistantPanel = ({ onClose }: { onClose: () => void }) => {
  const { messages, pending, send, clear, pageContext, debateNodeId, endDebate } = useAssistant();
  const [draft, setDraft] = useState("");
  const [recording, setRecording] = useState<Recording | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => inputRef.current?.focus(), [debateNodeId]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, pending, recording]);

  if (!pageContext) return null;
  const index = indexAnalysis(pageContext.analysis);
  const selected = pageContext.selectedNodeId
    ? index.get(pageContext.selectedNodeId)
    : undefined;
  const debateNode = debateNodeId ? index.get(debateNodeId) : undefined;
  const recordingNode = recording ? index.get(recording.nodeId) : undefined;

  const submit = (question: string) => {
    if (!question.trim() || pending) return;
    send(question);
    setDraft("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit(draft);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit(draft);
    }
  };

  const debateMessages = messages.slice(messages.findLastIndex((m) => m.role === "event") + 1);
  const reasonLabels = new Set<string>(Object.values(CONTESTATION_REASON_LABELS));

  /** What the analyst wrote since the debate started (reason chips excluded) */
  const debateArgument = () =>
    debateMessages
      .filter((m): m is Extract<ChatMessage, { role: "user" }> => m.role === "user")
      .map((m) => m.text)
      .filter((text) => !reasonLabels.has(text))
      .join("\n");

  /** Most specific reason identified during the debate (latest non-"other") */
  const debateReason = (fallback: ContestationReason) =>
    debateMessages
      .flatMap((m) => (m.role === "assistant" ? m.answer.actions ?? [] : []))
      .map((a) => a.reason)
      .filter((r) => r !== "other")
      .at(-1) ?? fallback;

  const last = messages.at(-1);
  const lastAnswer = last?.role === "assistant" ? last.answer : undefined;

  return (
    <section
      id={PANEL_ID}
      role="dialog"
      aria-label="Assistente da análise"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      className="fixed right-4 bottom-20 z-40 flex h-[min(36rem,calc(100dvh-7rem))] w-[min(25rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
    >
      <header className="flex items-start gap-2 border-b border-border px-4 py-3">
        <Bot className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Assistente da análise</h2>
          <p className="text-xs text-fg-muted">
            Explica notas e evidências · versão de demonstração
          </p>
        </div>
        <button
          type="button"
          className="btn-ghost p-1.5"
          onClick={() => {
            clear();
            setRecording(null);
          }}
          disabled={messages.length === 0}
          aria-label="Limpar conversa"
          title="Limpar conversa"
        >
          <RotateCcw className="size-4" aria-hidden />
        </button>
        <button
          type="button"
          className="btn-ghost p-1.5"
          onClick={onClose}
          aria-label="Fechar assistente"
        >
          <X className="size-4" aria-hidden />
        </button>
      </header>

      {debateNode ? (
        <div className="flex items-center gap-2 border-b border-score-moderate bg-score-moderate-soft px-4 py-1.5 text-xs">
          <Flag className="size-3.5 shrink-0 text-score-moderate" aria-hidden />
          <span className="min-w-0 flex-1 truncate">
            Contestando <strong>{debateNode.number} {getNodeTitle(debateNode)}</strong>
          </span>
          <button
            type="button"
            className="shrink-0 font-medium text-accent hover:underline"
            onClick={() => {
              setRecording(null);
              endDebate();
            }}
          >
            Encerrar
          </button>
        </div>
      ) : (
        <p className="truncate border-b border-border bg-surface-muted px-4 py-1.5 text-xs text-fg-muted">
          Sobre:{" "}
          <span className="font-medium text-fg">
            {selected
              ? `${selected.number} ${getNodeTitle(selected)}`
              : pageContext.screen === "decision"
                ? `documento de decisão · ${FRAMEWORKS[pageContext.analysis.framework].label} (cite um número, ex.: 3.1.1)`
                : "toda a análise (selecione um item para focar)"}
          </span>
        </p>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-3 text-sm">
            <p>
              Pergunte sobre as notas, as evidências e de onde vem cada
              informação. Eu explico; a decisão é sua. Discorda de algo? Use
              “Questionar” no detalhe do item.
            </p>
            <Suggestions items={starterSuggestions(pageContext)} onPick={submit} />
          </div>
        )}
        {messages.map((message) => (
          <Message
            key={message.id}
            message={message}
            onAction={(action) => setRecording(action)}
            actionsEnabled={message === last && !recording}
          />
        ))}
        {pending && (
          <p role="status" className="flex items-center gap-1.5 text-sm text-fg-muted">
            <span className="flex gap-0.5" aria-hidden>
              <span className="size-1.5 animate-bounce rounded-full bg-fg-muted" />
              <span className="size-1.5 animate-bounce rounded-full bg-fg-muted [animation-delay:150ms]" />
              <span className="size-1.5 animate-bounce rounded-full bg-fg-muted [animation-delay:300ms]" />
            </span>
            Analisando…
          </p>
        )}
        {!pending && !recording && lastAnswer && lastAnswer.suggestions.length > 0 && (
          <Suggestions items={lastAnswer.suggestions} onPick={submit} />
        )}
        {recording && recordingNode && (
          <ContestationForm
            analysis={pageContext.analysis}
            node={recordingNode}
            initialReason={debateReason(recording.reason)}
            initialArgument={debateArgument()}
            onCancel={() => setRecording(null)}
            onRecorded={(label) => {
              setRecording(null);
              endDebate(`Contestação de ${label} registrada na trilha`);
            }}
          />
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-border p-3">
        <div className="flex items-end gap-2">
          <label htmlFor="assistant-input" className="sr-only">
            {debateNode ? "Seu argumento" : "Pergunta para o assistente"}
          </label>
          <textarea
            ref={inputRef}
            id="assistant-input"
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              debateNode
                ? "Explique por que discorda…"
                : "Ex.: Como a nota deste critério foi calculada?"
            }
            className="input max-h-28 min-h-10 flex-1 resize-none"
          />
          <button
            type="submit"
            className="btn-primary size-10 shrink-0 p-0"
            disabled={pending || !draft.trim()}
            aria-label="Enviar"
          >
            <SendHorizontal className="size-4" aria-hidden />
          </button>
        </div>
        <p className="mt-1.5 text-[11px] text-fg-muted">
          Respostas automáticas de apoio. Não substituem a análise nem a decisão do analista.
        </p>
      </form>
    </section>
  );
};

const Suggestions = ({ items, onPick }: { items: string[]; onPick: (q: string) => void }) => (
  <ul className="flex flex-wrap gap-1.5" aria-label="Sugestões">
    {items.map((item) => (
      <li key={item}>
        <button
          type="button"
          onClick={() => onPick(item)}
          className="rounded-full border border-accent/40 bg-accent-soft px-2.5 py-1 text-left text-xs text-accent hover:border-accent"
        >
          {item}
        </button>
      </li>
    ))}
  </ul>
);

const Message = ({
  message,
  onAction,
  actionsEnabled,
}: {
  message: ChatMessage;
  onAction: (action: Recording) => void;
  actionsEnabled: boolean;
}) => {
  if (message.role === "user") {
    return (
      <p className="ml-8 rounded-lg rounded-br-sm bg-accent px-3 py-2 text-sm whitespace-pre-line text-accent-fg">
        {message.text}
      </p>
    );
  }
  if (message.role === "error") {
    return (
      <p role="alert" className="mr-8 rounded-lg bg-score-weak-soft px-3 py-2 text-sm text-danger">
        {message.text}
      </p>
    );
  }
  if (message.role === "event") {
    return (
      <p className="flex items-center gap-2 text-xs text-fg-muted">
        <span className="h-px flex-1 bg-border" />
        <Flag className="size-3.5 text-score-moderate" aria-hidden />
        {message.text}
        <span className="h-px flex-1 bg-border" />
      </p>
    );
  }
  return (
    <AnswerView answer={message.answer} onAction={onAction} actionsEnabled={actionsEnabled} />
  );
};

const AnswerView = ({
  answer,
  onAction,
  actionsEnabled,
}: {
  answer: AssistantAnswer;
  onAction: (action: Recording) => void;
  actionsEnabled: boolean;
}) => {
  const openNode = useOpenNode();

  return (
    <div className="mr-4 space-y-2 rounded-lg rounded-bl-sm bg-surface-muted px-3 py-2 text-sm leading-relaxed">
      {answer.blocks.map((block, i) => {
        if (block.type === "text") return <p key={i}>{block.text}</p>;
        if (block.type === "list") {
          return (
            <ul key={i} className="list-disc space-y-0.5 pl-5">
              {block.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          );
        }
        return (
          <figure key={i} className="rounded-md border border-border bg-surface p-2">
            <blockquote className="italic">“{block.text}”</blockquote>
            <figcaption className="mt-1 text-xs text-fg-muted">{block.caption}</figcaption>
          </figure>
        );
      })}
      {answer.sources.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="mb-1 text-xs font-medium text-fg-muted">Fontes</p>
          <ul className="flex flex-wrap gap-1">
            {answer.sources.map((s) => (
              <li key={s.nodeId}>
                <button
                  type="button"
                  onClick={() => openNode(s.nodeId)}
                  className="max-w-full truncate rounded border border-border bg-surface px-1.5 py-0.5 text-xs hover:border-accent hover:text-accent"
                  title={`Ir para ${s.label}`}
                >
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {actionsEnabled && answer.actions?.map((action) => (
        <button
          key={action.type + action.nodeId}
          type="button"
          className="btn-secondary w-full border-score-moderate py-1.5"
          onClick={() => onAction(action)}
        >
          <Flag className="size-4 text-score-moderate" aria-hidden />
          Registrar contestação
        </button>
      ))}
    </div>
  );
};

/**
 * Sources are clickable: on the analysis screen they select the node (graph,
 * tree and detail follow the URL); on the decision document they scroll to it.
 */
const useOpenNode = () => {
  const { pageContext } = useAssistant();
  const navigate = useNavigate();
  const { projectId = "" } = useParams();

  return (nodeId: string) => {
    if (pageContext?.screen === "analysis") {
      navigate(paths.analysis(projectId, nodeId, pageContext.analysis.framework));
      return;
    }
    if (!pageContext) return;
    const target = document.getElementById(reportAnchorId(pageContext.analysis, nodeId));
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    target?.animate(
      [{ backgroundColor: "var(--color-accent-soft)" }, { backgroundColor: "transparent" }],
      { duration: 1600, easing: "ease-out" },
    );
  };
};
