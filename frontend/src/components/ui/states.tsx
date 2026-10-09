import { CircleAlert, Inbox, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

/* Loading / empty / error states shared by every screen */

export const LoadingState = ({ label = "Carregando…" }: { label?: string }) => (
  <div
    role="status"
    className="flex flex-1 items-center justify-center gap-2 p-10 text-fg-muted"
  >
    <LoaderCircle className="size-5 animate-spin text-action" aria-hidden />
    <span>{label}</span>
  </div>
);

interface MessageStateProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}

const MessageState = ({ title, description, action, icon }: MessageStateProps) => (
  <div className="flex flex-1 flex-col items-center justify-center gap-2 p-10 text-center">
    {icon}
    <p className="text-base leading-5 font-semibold">{title}</p>
    {description && (
      <p className="max-w-md text-sm text-fg-muted">{description}</p>
    )}
    {action && <div className="mt-2">{action}</div>}
  </div>
);

export const EmptyState = (props: Omit<MessageStateProps, "icon">) => (
  <MessageState
    {...props}
    icon={
      <span className="mb-1 flex size-14 items-center justify-center rounded-full bg-surface-sunken">
        <Inbox className="size-7 text-fg-secondary" aria-hidden />
      </span>
    }
  />
);

export const ErrorState = ({
  title = "Algo deu errado",
  error,
  onRetry,
  action,
}: {
  title?: string;
  error?: unknown;
  onRetry?: () => void;
  /** Extra way out, e.g. a link back to the project list */
  action?: ReactNode;
}) => (
  <div role="alert" className="contents">
    <MessageState
      title={title}
      description={error instanceof Error ? error.message : undefined}
      icon={
        <span className="mb-1 flex size-14 items-center justify-center rounded-full bg-state-negative-soft">
          <CircleAlert className="size-7 text-danger" aria-hidden />
        </span>
      }
      action={
        (onRetry || action) && (
          <div className="flex flex-wrap justify-center gap-2">
            {onRetry && (
              <button type="button" className="btn-secondary" onClick={onRetry}>
                Tentar novamente
              </button>
            )}
            {action}
          </div>
        )
      }
    />
  </div>
);
