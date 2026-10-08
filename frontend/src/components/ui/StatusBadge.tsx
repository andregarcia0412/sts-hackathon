import { CircleAlert, CircleCheckBig, FileSearch, LoaderCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { PROJECT_STATUS_LABELS } from "@/domain/labels";
import type { ProjectStatus } from "@/domain/types";

const STATUS_STYLES: Record<
  ProjectStatus,
  { className: string; Icon: LucideIcon; iconClassName?: string }
> = {
  processing: {
    className: "bg-surface-muted text-fg-muted",
    Icon: LoaderCircle,
    iconClassName: "animate-spin",
  },
  ready: { className: "bg-accent-soft text-accent", Icon: FileSearch },
  decided: { className: "bg-score-strong-soft text-score-strong", Icon: CircleCheckBig },
  error: { className: "bg-score-weak-soft text-danger", Icon: CircleAlert },
};

export const StatusBadge = ({ status }: { status: ProjectStatus }) => {
  const { className, Icon, iconClassName } = STATUS_STYLES[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${className}`}
    >
      <Icon className={`size-3.5 ${iconClassName ?? ""}`} aria-hidden />
      {PROJECT_STATUS_LABELS[status]}
    </span>
  );
};
