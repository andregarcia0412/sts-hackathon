import type { ComponentType, SVGProps } from "react";
import {
  ArticleIcon,
  CheckIndeterminateIcon,
  CheckSmallIcon,
  HelpOutlineIcon,
  LanguageIcon,
  WarningAmberIcon,
} from "@/components/icons/MaterialIcons";

const ITEMS: { Icon: ComponentType<SVGProps<SVGSVGElement>>; label: string; className: string }[] = [
  { Icon: CheckSmallIcon, label: "Evidência positiva", className: "text-state-positive-strong" },
  { Icon: CheckIndeterminateIcon, label: "Evidência negativa", className: "text-accent" },
  { Icon: WarningAmberIcon, label: "Contraditório ou parcial", className: "text-state-attention-strong" },
  { Icon: HelpOutlineIcon, label: "Sem evidência", className: "text-state-neutral" },
  { Icon: ArticleIcon, label: "Documento do projeto", className: "text-fg-secondary" },
  { Icon: LanguageIcon, label: "Web", className: "text-fg-secondary" },
];

export const GraphLegend = () => (
  <div aria-label="Legenda" className="flex w-48 flex-col gap-1.5 rounded-lg bg-surface-sunken p-2">
    <p className="text-[13px] leading-4 font-semibold tracking-[0.06em] text-black uppercase">
      Legenda:
    </p>
    <ul className="flex flex-col gap-1.5">
      {ITEMS.map(({ Icon, label, className }) => (
        <li key={label} className="flex items-center gap-1.5 text-xs leading-4 text-fg-secondary">
          <Icon className={`size-4 shrink-0 ${className}`} />
          {label}
        </li>
      ))}
    </ul>
  </div>
);
