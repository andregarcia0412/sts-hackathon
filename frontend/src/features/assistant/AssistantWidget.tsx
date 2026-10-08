import { Flag, RefreshCcw, RotateCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { AssistantAction, AssistantAnswer, ChatMessage } from "@/domain/assistant";
import { CONTESTATION_REASON_LABELS } from "@/domain/labels";
import type { Contestation, ContestationReason } from "@/domain/types";
import { useRequestReanalysis } from "@/services/queries";
import { AssistantStarIcon, SendIcon } from "@/components/icons/AssistantIcons";
import { FRAMEWORKS } from "@/domain/frameworks";
import { getNodeTitle, indexAnalysis } from "@/domain/tree";
import { ContestationForm } from "@/features/assistant/ContestationForm";
import { useAssistant } from "@/features/assistant/assistantState";
import { starterSuggestions } from "@/mocks/assistantEngine";
import { paths, reportAnchorId } from "@/routes/paths";

const PANEL_ID = "analysis-assistant";

/** Quick questions shown above the input, as in the design */
const MAX_SUGGESTIONS = 3;

/**
 * Floating assistant ("IA Assistente", bottom-right) for the analysis and
 * decision screens. Answers explain scores and evidences, never give a verdict,
 * and link back to the nodes they are based on. In debate mode the analyst
 * contests a node.
 */
export const AssistantWidget = () => {
  const { open, setOpen, pageContext } = useAssistant();
  const launcherRef = useRef<HTMLButtonElement>(null);
  // The panel stays mounted while its closing animation plays
  const [mounted, setMounted] = useState(open);
  if (open && !mounted) setMounted(true);

  // Only screens that registered a context (analysis/decision with data) get the bot
  if (!pageContext) return null;

  const close = () => {
    setOpen(false);
    launcherRef.current?.focus();
  };

  return (
    <div className="print:hidden">
      {mounted && <AssistantPanel onClose={close} closing={!open} onClosed={() => setMounted(false)} />}
      <button
        ref={launcherRef}
        type="button"
        aria-expanded={open}
        aria-controls={PANEL_ID}
        aria-label={open ? "Fechar assistente" : "Abrir assistente da análise"}
        onClick={() => (open ? close() : setOpen(true))}
        className="fixed right-4 bottom-4 z-40 flex size-14 items-center justify-center rounded-full bg-action text-white shadow-card-accent transition-transform hover:scale-105 sm:size-18"
      >
        <AssistantStarIcon
          className={`absolute size-7 transition-[rotate,scale,opacity] duration-300 sm:size-8 ${open ? "scale-50 rotate-90 opacity-0" : ""}`}
        />
        <X
          className={`absolute size-7 transition-[rotate,scale,opacity] duration-300 ${open ? "" : "scale-50 -rotate-90 opacity-0"}`}
          aria-hidden
        />
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

const roundButton =
  "flex shrink-0 items-center justify-center rounded-full border border-fg-faint bg-surface text-fg transition-colors hover:bg-surface-muted disabled:opacity-40 disabled:hover:bg-surface";

const AssistantPanel = ({
  onClose,
  closing,
  onClosed,
}: {
  onClose: () => void;
  /** Playing the closing animation; unmounts on `onClosed` */
  closing: boolean;
  onClosed: () => void;
}) => {
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
  const suggestions =
    messages.length === 0
      ? starterSuggestions(pageContext)
      : !pending && !recording && lastAnswer
        ? lastAnswer.suggestions
        : [];

  return (
    <section
      id={PANEL_ID}
      role="dialog"
      aria-label="Assistente da análise"
      inert={closing}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      onAnimationEnd={(e) => {
        if (closing && e.target === e.currentTarget) onClosed();
      }}
      className={`assistant-motion fixed right-4 bottom-22 isolate z-40 flex h-[min(34rem,calc(100dvh-7.5rem))] w-[min(30.625rem,calc(100vw-2rem))] origin-bottom-right flex-col overflow-hidden rounded-2xl border border-divider bg-surface p-5 shadow-float sm:bottom-26 sm:h-[min(34rem,calc(100dvh-8.5rem))] ${
        closing ? "animate-assistant-out" : "animate-assistant-in"
      }`}
    >
      {/* Wine and orange glow at the bottom, as in the design */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-72 opacity-50">
        <div className="absolute -bottom-10 left-[18%] size-52 rounded-full bg-action blur-[70px]" />
        <div className="absolute right-[18%] -bottom-10 size-52 rounded-full bg-brand-orange blur-[70px]" />
      </div>

      <header className="flex items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-action">IA Assistente</h2>
        <div className="flex gap-2">
          <button
            type="button"
            className={`${roundButton} size-12`}
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
            <RotateCcw className="size-5" aria-hidden />
          </button>
          <button type="button" className={`${roundButton} size-12`} onClick={onClose} aria-label="Fechar assistente">
            <X className="size-6" aria-hidden />
          </button>
        </div>
      </header>

      {debateNode ? (
        <div className="mt-3 flex items-center gap-2 rounded-xl bg-state-attention-soft px-3 py-2 text-xs leading-4 text-state-attention-strong">
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
        <p className="mt-1 text-xs leading-4 break-words text-fg-muted">
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

      <div className="-mx-1 flex flex-1 flex-col gap-4 overflow-y-auto px-1 py-4" aria-live="polite">
        {messages.length === 0 && (
          <div className="my-auto flex flex-col items-center gap-2 text-center">
            <AssistantStarIcon gradient className="size-11" />
            <p className="text-2xl text-action">Envie uma mensagem para iniciar</p>
            <p className="max-w-xs text-xs leading-4 text-fg-muted">
              Pergunte sobre as notas, as evidências e de onde vem cada informação. Eu explico; a
              decisão é sua. Discorda de algo? Use “Questionar” no detalhe do item.
            </p>
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
          <p role="status" className="flex w-fit gap-1 rounded-3xl rounded-bl-none bg-surface-sunken px-6 py-4">
            <span className="sr-only">Analisando…</span>
            <span className="size-1.5 animate-bounce rounded-full bg-fg-secondary" aria-hidden />
            <span className="size-1.5 animate-bounce rounded-full bg-fg-secondary [animation-delay:150ms]" aria-hidden />
            <span className="size-1.5 animate-bounce rounded-full bg-fg-secondary [animation-delay:300ms]" aria-hidden />
          </p>
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

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        {suggestions.length > 0 && <Suggestions items={suggestions.slice(0, MAX_SUGGESTIONS)} onPick={submit} />}
        <div className="flex items-end gap-2 rounded-3xl border border-border-strong bg-surface py-1 pr-1.5 pl-4 focus-within:outline-2 focus-within:outline-action">
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
            placeholder={debateNode ? "Explique por que discorda…" : "Digite sua mensagem..."}
            className="max-h-28 min-h-10 flex-1 resize-none bg-transparent py-2.5 text-sm leading-5 field-sizing-content placeholder:text-fg-muted focus-visible:outline-none"
          />
          <button
            type="submit"
            className="mb-0.5 flex size-9 shrink-0 items-center justify-center rounded-full text-action transition-colors hover:bg-accent-soft disabled:text-fg-faint disabled:hover:bg-transparent"
            disabled={pending || !draft.trim()}
            aria-label="Enviar"
          >
            <SendIcon className="size-6" />
          </button>
        </div>
        <p className="text-[11px] leading-4 text-fg-muted">
          Respostas automáticas de apoio. Não substituem a análise nem a decisão do analista.
        </p>
      </form>
    </section>
  );
};

const Suggestions = ({ items, onPick }: { items: string[]; onPick: (q: string) => void }) => (
  <ul className="flex flex-wrap gap-2" aria-label="Sugestões">
    {items.map((item) => (
      <li key={item} className="flex grow basis-32">
        <button
          type="button"
          onClick={() => onPick(item)}
          className="w-full rounded-[20px] bg-accent px-3 py-2 text-left text-xs leading-4 text-white transition-[filter] hover:brightness-110"
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
      <p className="ml-auto w-fit max-w-[85%] rounded-3xl rounded-br-none bg-brand-blush px-5 py-3 text-sm leading-5 break-words whitespace-pre-line text-fg">
        {message.text}
      </p>
    );
  }
  if (message.role === "error") {
    return (
      <p role="alert" className="mr-8 w-fit rounded-3xl rounded-bl-none bg-state-negative-soft px-5 py-3 text-sm leading-5 text-danger">
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
    <div className="mr-6 space-y-2 rounded-3xl rounded-bl-none bg-surface-sunken px-5 py-3 text-sm leading-5">
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
        <div className="border-t border-border-strong pt-2">
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
