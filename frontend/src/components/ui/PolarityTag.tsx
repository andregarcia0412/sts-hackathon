import { POLARITY_ICONS, POLARITY_STYLES } from "@/components/ui/polarityStyles";
import { POLARITY_LABELS } from "@/domain/labels";
import type { EvidencePolarity } from "@/domain/types";

export const PolarityTag = ({ polarity }: { polarity: EvidencePolarity }) => {
  const Icon = POLARITY_ICONS[polarity];
  const styles = POLARITY_STYLES[polarity];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${styles.soft} ${styles.text}`}
    >
      <Icon className="size-3.5" aria-hidden />
      Evidência {POLARITY_LABELS[polarity].toLowerCase()}
    </span>
  );
};
