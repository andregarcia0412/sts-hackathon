import { CircleSlash, PenLine } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { ArticleIcon, LanguageIcon } from "@/components/icons/MaterialIcons";
import type { EvidenceSourceKind } from "@/domain/evidence";

export const SOURCE_ICONS: Record<EvidenceSourceKind, ComponentType<SVGProps<SVGSVGElement>>> = {
  document: ArticleIcon,
  web: LanguageIcon,
  text: PenLine,
  none: CircleSlash,
};
