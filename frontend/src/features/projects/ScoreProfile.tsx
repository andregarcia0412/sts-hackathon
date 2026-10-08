import { Tag } from "@/components/ui/Tag";
import { CRITERION_STATUS, criterionStatus } from "@/domain/qualitative";
import { scoreBand } from "@/domain/score";
import type { CriterionScoreSummary } from "@/domain/types";

/* Static class names so Tailwind can see them */
const BAR_FILL = {
  strong: "bg-state-positive",
  moderate: "bg-state-attention",
  weak: "bg-state-negative",
} as const;

/**
 * Tiny profile of a project's criteria (one bar per criterion, height = score)
 * plus the weakest one: enough to triage hundreds of projects.
 */
export const ScoreProfile = ({ scores }: { scores: CriterionScoreSummary[] }) => {
  const weakest = scores.reduce((min, s) => (s.score < min.score ? s : min), scores[0]);
  const status = CRITERION_STATUS[criterionStatus(weakest)];
  const description = scores.map((s) => `${s.name} ${s.score}`).join(", ");

  return (
    <div className="flex items-center gap-3">
      <span className="flex h-8 items-end gap-0.5" title={description} aria-hidden>
        {scores.map((s) => (
          <span
            key={s.criterionKey}
            className={`w-1.5 rounded-t-sm ${BAR_FILL[scoreBand(s.score)]}`}
            style={{ height: `${Math.max(10, s.score)}%` }}
          />
        ))}
      </span>
      <span className="sr-only">Força da evidência por critério: {description}.</span>
      <span className="flex min-w-0 flex-col items-start gap-1">
        <span className="text-sm leading-5 font-medium">
          {weakest.name} <span className="font-normal text-fg-muted tabular-nums">{weakest.score}</span>
        </span>
        <Tag tone={status.tone} label={status.label} size="sm" />
      </span>
    </div>
  );
};
