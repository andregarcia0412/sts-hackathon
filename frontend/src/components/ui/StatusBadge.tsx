import { LoaderCircle } from "lucide-react";
import { Tag } from "@/components/ui/Tag";
import { PROJECT_STATUS_LABELS, PROJECT_STATUS_TONES } from "@/domain/labels";
import type { ProjectStatus } from "@/domain/types";

/** Project status as an "Etiqueta"; processing spins */
export const StatusBadge = ({ status, size = "sm" }: { status: ProjectStatus; size?: "sm" | "md" }) => (
  <Tag
    tone={PROJECT_STATUS_TONES[status]}
    label={PROJECT_STATUS_LABELS[status]}
    size={size}
    icon={status === "processing" ? LoaderCircle : undefined}
    iconClassName={status === "processing" ? "animate-spin" : ""}
  />
);
