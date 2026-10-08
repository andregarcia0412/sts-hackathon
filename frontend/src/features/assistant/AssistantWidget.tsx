import {
  Bot,
  Flag,
  RefreshCcw,
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
import type { Contestation, ContestationReason } from "@/domain/types";
import { useRequestReanalysis } from "@/services/queries";
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
        className="fixed right-4 bottom-4 z-40 flex size-14 items-center justify-center rounded-full bg-action text-white shadow-card-accent transition-transform hover:scale-105"
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

/** The model's reanalysis, told as an assistant answer */
const reanalysisAnswer = (contestation: Contestation): AssistantAnswer => {
  const resolution = contestation.resolution;
  if (!resolution) {
    return { blocks: [{ type: "text", text: "A reanálise não terminou." }], sources: [], suggestions: [] };
  }
  return {
    blocks: [
      {
        type: "text",
        text: resolution.verdict === "accepted" ? "Reanálise concluída: contestação acatada." : "Reanálise concluída: mantive a leitura.",
      },
      { type: "text", text: resolution.explanation },
      ...(resolution.changes.length
        ? [{ type: "text" as const, text: "A árvore de evidências e o documento de decisão já mostram os valores revisados." }]
        : []),
    ],
    sources: [
      { nodeId: contestation.nodeId, label: contestation.nodeLabel },
      ...resolution.changes
        .filter((c) => c.nodeId !== contestation.nodeId)
        .map((c) => ({ nodeId: c.nodeId, label: c.nodeLabel })),
    ],
    suggestions: [],
  };
};

const AssistantPanel = ({ onClose }: { onClose: () => void }) => {
  const { messages, pending, send, clear, pageContext, debateNodeId, endDebate, respondWith } =
    useAssistant();
  const reanalysis = useRequestReanalysis();
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
      .flatMap((a) => (a.type === "record-contestation" ? [a.reason] : []))
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
      className="fixed right-4 bottom-22 z-40 flex h-[min(38rem,calc(100dvh-7.5rem))] w-[min(26rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_12px_32px_rgb(22_22_22/0.18)]"
    >
      <header className="flex items-center gap-3 bg-brand-deep px-4 py-3 text-white">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white/15">
          <Bot className="size-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-base leading-5 font-semibold">Assistente da análise</h2>
          <p className="text-xs leading-4 text-brand-blush">
            Explica notas e evidências · versão de demonstração
          </p>
        </div>
        <button
          type="button"
          className="rounded-full p-2 text-white/90 transition-colors hover:bg-white/15 disabled:opacity-40 disabled:hover:bg-transparent"
          onClick={() => {
            clear();
            setRecording(null);
            // The button disables itself: keep focus (and Escape) inside the panel
            inputRef.current?.focus();
          }}
          disabled={messages.length === 0}
          aria-label="Limpar conversa"
          title="Limpar conversa"
        >
          <RotateCcw className="size-4" aria-hidden />
        </button>
        <button
          type="button"
          className="rounded-full p-2 text-white/90 transition-colors hover:bg-white/15"
          onClick={onClose}
          aria-label="Fechar assistente"
        >
          <X className="size-4" aria-hidden />
        </button>
      </header>

      {debateNode ? (
        <div className="flex items-center gap-2 bg-state-attention-soft px-4 py-2 text-xs leading-4 text-state-attention-strong">
          <Flag className="size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 break-words">
            Contestando <strong>{debateNode.number} {getNodeTitle(debateNode)}</strong>
          </span>
          <button
            type="button"
            className="btn-link shrink-0"
            onClick={() => {
              setRecording(null);
              endDebate();
            }}
          >
            Encerrar
          </button>
        </div>
      ) : (
        <p className="bg-accent-soft px-4 py-2 break-words text-xs leading-4 text-fg-muted">
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
          <div className="space-y-3 text-sm leading-5">
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
            onAction={(action) => {
              if (action.type === "record-contestation") {
                setRecording(action);
              } else {
                respondWith(reanalysis.mutateAsync(action.contestationId).then(reanalysisAnswer));
              }
            }}
            actionsEnabled={message === last && !recording}
          />
        ))}
        {pending && (
          <p role="status" className="flex items-center gap-1.5 text-sm text-fg-muted">
            <span className="flex gap-0.5" aria-hidden>
              <span className="size-1.5 animate-bounce rounded-full bg-action" />
              <span className="size-1.5 animate-bounce rounded-full bg-action [animation-delay:150ms]" />
              <span className="size-1.5 animate-bounce rounded-full bg-action [animation-delay:300ms]" />
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
            onRecorded={(contestation) => {
              setRecording(null);
              endDebate(`Contestação de ${contestation.nodeLabel} registrada na trilha`);
              respondWith(
                Promise.resolve({
                  blocks: [
                    {
                      type: "text",
                      text: "Contestação registrada como aberta. Posso reanalisar agora: se o seu argumento indicar uma fonte verificável, eu acato e ajusto a análise; senão, explico por que mantenho a leitura.",
                    },
                  ],
                  sources: [{ nodeId: contestation.nodeId, label: contestation.nodeLabel }],
                  suggestions: [],
                  actions: [
                    { type: "request-reanalysis", contestationId: contestation.id, nodeId: contestation.nodeId },
                  ],
                }),
              );
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
            className="input max-h-28 min-h-12 flex-1 resize-none field-sizing-content"
          />
          <button
            type="submit"
            className="btn-primary size-12 shrink-0 p-0"
            disabled={pending || !draft.trim()}
            aria-label="Enviar"
          >
            <SendHorizontal className="size-5" aria-hidden />
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-4 text-fg-muted">
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
          className="rounded-full border border-action/40 bg-accent-soft px-3 py-1.5 text-left text-xs leading-4 font-medium text-accent transition-colors hover:border-action"
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
  onAction: (action: AssistantAction) => void;
  actionsEnabled: boolean;
}) => {
  if (message.role === "user") {
    return (
      <p className="ml-8 rounded-2xl rounded-br-md bg-action px-3.5 py-2.5 text-sm leading-5 whitespace-pre-line text-white">
        {message.text}
      </p>
    );
  }
  if (message.role === "error") {
    return (
      <p role="alert" className="mr-8 rounded-2xl rounded-bl-md bg-state-negative-soft px-3.5 py-2.5 text-sm leading-5 text-danger">
        {message.text}
      </p>
    );
  }
  if (message.role === "event") {
    return (
      <p className="flex items-center gap-2 text-xs text-fg-muted">
        <span className="h-px flex-1 bg-border" />
        <Flag className="size-3.5 text-state-attention" aria-hidden />
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
  onAction: (action: AssistantAction) => void;
  actionsEnabled: boolean;
}) => {
  const openNode = useOpenNode();

  return (
    <div className="mr-4 space-y-2 rounded-2xl rounded-bl-md border border-border bg-surface-muted px-3.5 py-2.5 text-sm leading-5">
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
          <figure key={i} className="rounded-lg border-l-2 border-action bg-surface px-3 py-2">
            <blockquote>“{block.text}”</blockquote>
            <figcaption className="mt-1 text-xs text-fg-muted">{block.caption}</figcaption>
          </figure>
        );
      })}
      {answer.sources.length > 0 && (
        <div className="border-t border-border pt-2">
          <p className="caps-label mb-1.5 text-fg-muted">Fontes</p>
          <ul className="flex flex-wrap gap-1">
            {answer.sources.map((s) => (
              <li key={s.nodeId}>
                <button
                  type="button"
                  onClick={() => openNode(s.nodeId)}
                  className="max-w-full rounded-2xl border border-border-strong bg-surface px-2.5 py-1 text-left text-xs break-words leading-4 font-medium transition-colors hover:border-action hover:text-accent"
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
          className="btn-secondary w-full px-4 py-2 text-sm"
          onClick={() => onAction(action)}
        >
          {action.type === "record-contestation" ? (
            <>
              <Flag className="size-4 text-state-attention" aria-hidden />
              Registrar contestação
            </>
          ) : (
            <>
              <RefreshCcw className="size-4 text-accent" aria-hidden />
              Reanalisar agora
            </>
          )}
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
