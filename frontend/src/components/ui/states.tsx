import { CircleAlert, Inbox, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

/* Loading / empty / error states shared by every screen */

export const LoadingState = ({ label = "Carregando…" }: { label?: string }) => (
  <div
    role="status"
    className="flex flex-1 items-center justify-center gap-2 p-10 text-fg-muted"
  >
    <LoaderCircle className="size-5 animate-spin" aria-hidden />
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
    <p className="font-medium">{title}</p>
    {description && (
      <p className="max-w-md text-sm text-fg-muted">{description}</p>
    )}
    {action && <div className="mt-2">{action}</div>}
  </div>
);

export const EmptyState = (props: Omit<MessageStateProps, "icon">) => (
  <MessageState
    {...props}
    icon={<Inbox className="size-8 text-fg-muted" aria-hidden />}
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
      icon={<CircleAlert className="size-8 text-danger" aria-hidden />}
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
