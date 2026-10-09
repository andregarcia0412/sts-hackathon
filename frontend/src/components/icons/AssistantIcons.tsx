import type { SVGProps } from "react";

/*
 * Icons of the assistant in the high-fidelity design (Figma "IA Assistente").
 */

type IconProps = SVGProps<SVGSVGElement>;

const STAR =
  "M19.81 1.9c.94-2.53 4.52-2.53 5.46 0l4.37 11.82c.3.8.92 1.42 1.72 1.72l11.82 4.37c2.53.94 2.53 4.52 0 5.46l-11.82 4.37c-.8.3-1.42.92-1.72 1.72l-4.37 11.82c-.94 2.53-4.52 2.53-5.46 0L15.44 31.36c-.3-.8-.92-1.42-1.72-1.72L1.9 25.27c-2.53-.94-2.53-4.52 0-5.46l11.82-4.37c.8-.3 1.42-.92 1.72-1.72L19.81 1.9Z";

/** Four-point star of the assistant; `gradient` = wine → orange, as in the empty state */
export const AssistantStarIcon = ({ gradient = false, ...props }: IconProps & { gradient?: boolean }) => (
  <svg viewBox="0 0 45.07 45.07" fill="currentColor" aria-hidden {...props}>
    {gradient && (
      <defs>
        <linearGradient id="assistant-star-gradient" x1="-5.5" y1="22.5" x2="50.6" y2="22.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--color-action)" />
          <stop offset="1" stopColor="var(--color-brand-orange)" />
        </linearGradient>
      </defs>
    )}
    <path d={STAR} fill={gradient ? "url(#assistant-star-gradient)" : undefined} />
  </svg>
);

/** Material "Send" (filled) */
export const SendIcon = (props: IconProps) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
    <path d="M4.4 19.43c-.33.13-.65.1-.95-.1-.3-.19-.45-.47-.45-.83v-3.73c0-.23.07-.44.2-.62.13-.18.32-.3.55-.35L11 12l-7.25-1.8a.94.94 0 0 1-.55-.35.98.98 0 0 1-.2-.63V5.5c0-.37.15-.65.45-.84.3-.19.62-.22.95-.09l15.4 6.5c.42.19.63.5.63.93 0 .43-.21.74-.63.93l-15.4 6.5Z" />
  </svg>
);
