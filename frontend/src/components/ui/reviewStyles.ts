import { CheckCheck, Flag, RefreshCcw } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReviewMarker } from "@/domain/contestations";

/* Static class names so Tailwind can see them */
export const REVIEW_MARKER_STYLES: Record<
  ReviewMarker,
  { Icon: LucideIcon; icon: string; tag: string }
> = {
  open: { Icon: Flag, icon: "text-score-moderate", tag: "bg-score-moderate-soft" },
  revised: { Icon: RefreshCcw, icon: "text-accent", tag: "bg-accent-soft" },
  resolved: { Icon: CheckCheck, icon: "text-fg-muted", tag: "bg-surface-muted" },
};
