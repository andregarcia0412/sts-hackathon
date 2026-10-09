import { Check, CircleHelp, Minus, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import {
  CheckIndeterminateIcon,
  CheckSmallIcon,
  HelpOutlineIcon,
  WarningAmberIcon,
} from "@/components/icons/MaterialIcons";
import type { Tone } from "@/domain/qualitative";

/* Static class names so Tailwind can see them */
export const TONE_STYLES: Record<
  Tone,
  { soft: string; text: string; strongText: string; icon: string; border: string }
> = {
  positive: {
    soft: "bg-state-positive-soft",
    text: "text-state-positive",
    strongText: "text-state-positive-strong",
    icon: "text-state-positive-strong",
    border: "border-state-positive",
  },
  attention: {
    soft: "bg-state-attention-soft",
    text: "text-state-attention",
    strongText: "text-state-attention-strong",
    icon: "text-state-attention-strong",
    border: "border-state-attention",
  },
  negative: {
    soft: "bg-state-negative-soft",
    text: "text-state-negative",
    strongText: "text-state-negative",
    icon: "text-accent",
    border: "border-state-negative",
  },
  neutral: {
    soft: "bg-state-neutral-soft",
    text: "text-state-neutral",
    strongText: "text-state-neutral",
    icon: "text-state-neutral",
    border: "border-border-strong",
  },
};

/** 24px Material icons of the large "Etiqueta" */
export const TONE_ICONS: Record<Tone, ComponentType<SVGProps<SVGSVGElement>>> = {
  positive: CheckSmallIcon,
  attention: WarningAmberIcon,
  negative: CheckIndeterminateIcon,
  neutral: HelpOutlineIcon,
};

/** 12px stroke icons of the compact "Etiqueta" */
export const TONE_SMALL_ICONS: Record<Tone, LucideIcon> = {
  positive: Check,
  attention: TriangleAlert,
  negative: Minus,
  neutral: CircleHelp,
};
