import { REVIEW_MARKER_STYLES } from "@/components/ui/reviewStyles";
import { REVIEW_MARKER_LABELS } from "@/domain/contestations";
import type { ReviewMarker } from "@/domain/contestations";

/** "contestado" / "revisado" / "contestação resolvida": icon + label, never color alone */
export const ReviewTag = ({ marker, size = "sm" }: { marker: ReviewMarker; size?: "xs" | "sm" }) => {
  const { Icon, icon, tag } = REVIEW_MARKER_STYLES[marker];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full font-medium whitespace-nowrap text-fg ${tag} ${
        size === "xs" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-0.5 text-xs"
      }`}
    >
      <Icon className={`${size === "xs" ? "size-3" : "size-3.5"} ${icon}`} aria-hidden />
      {REVIEW_MARKER_LABELS[marker]}
    </span>
  );
};
