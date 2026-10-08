import type { ComponentType, SVGProps } from "react";
import { TONE_ICONS, TONE_SMALL_ICONS, TONE_STYLES } from "@/components/ui/toneStyles";
import type { Tone } from "@/domain/qualitative";

interface TagProps {
  tone: Tone;
  label: string;
  /** md: pill with 24px icon (graph, headers); sm: compact (lists) */
  size?: "md" | "sm";
  /** Only the icon (the label is read by screen readers and shown as a tooltip) */
  iconOnly?: boolean;
  /** Replaces the tone's icon (e.g. a spinner for "Processando") */
  icon?: ComponentType<SVGProps<SVGSVGElement>>;
  iconClassName?: string;
  className?: string;
}

/** "Etiqueta" of the design system: state or qualitative score, always icon + text */
export const Tag = ({
  tone,
  label,
  size = "md",
  iconOnly = false,
  icon,
  iconClassName = "",
  className = "",
}: TagProps) => {
  const styles = TONE_STYLES[tone];

  if (size === "sm") {
    const Icon = icon ?? TONE_SMALL_ICONS[tone];
    return (
      <span
        className={`inline-flex shrink-0 items-center gap-1 rounded py-0.5 pr-2 pl-1.5 text-xs leading-4 font-medium whitespace-nowrap ${styles.soft} ${styles.text} ${className}`}
      >
        <Icon className={`size-3 stroke-[2.5] ${iconClassName}`} aria-hidden />
        {label}
      </span>
    );
  }

  const Icon = icon ?? TONE_ICONS[tone];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs leading-4 font-medium whitespace-nowrap ${styles.soft} ${styles.strongText} ${className}`}
      title={iconOnly ? label : undefined}
    >
      <Icon className={`size-6 ${styles.icon} ${iconClassName}`} aria-hidden />
      {iconOnly ? <span className="sr-only">{label}</span> : label}
    </span>
  );
};
