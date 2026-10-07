import { SignalHigh, SignalLow, SignalMedium } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ScoreBand } from "@/domain/score";

/* Static class names so Tailwind can see them */
export const SCORE_BAND_STYLES: Record<
  ScoreBand,
  { text: string; soft: string; border: string; fill: string }
> = {
  strong: {
    text: "text-score-strong",
    soft: "bg-score-strong-soft",
    border: "border-score-strong",
    fill: "bg-score-strong",
  },
  moderate: {
    text: "text-score-moderate",
    soft: "bg-score-moderate-soft",
    border: "border-score-moderate",
    fill: "bg-score-moderate",
  },
  weak: {
    text: "text-score-weak",
    soft: "bg-score-weak-soft",
    border: "border-score-weak",
    fill: "bg-score-weak",
  },
};

export const SCORE_BAND_ICONS: Record<ScoreBand, LucideIcon> = {
  strong: SignalHigh,
  moderate: SignalMedium,
  weak: SignalLow,
};
