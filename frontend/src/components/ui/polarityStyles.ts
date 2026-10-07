import { CircleMinus, CirclePlus } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { EvidencePolarity } from "@/domain/types";

/* Static class names so Tailwind can see them */
export const POLARITY_STYLES: Record<
  EvidencePolarity,
  { text: string; soft: string; border: string; fill: string }
> = {
  positive: {
    text: "text-evidence-positive",
    soft: "bg-evidence-positive-soft",
    border: "border-evidence-positive",
    fill: "bg-evidence-positive",
  },
  negative: {
    text: "text-evidence-negative",
    soft: "bg-evidence-negative-soft",
    border: "border-evidence-negative",
    fill: "bg-evidence-negative",
  },
};

export const POLARITY_ICONS: Record<EvidencePolarity, LucideIcon> = {
  positive: CirclePlus,
  negative: CircleMinus,
};
