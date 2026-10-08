import { SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";
import type { CriterionScoreSummary } from "@/domain/types";

/**
 * Tiny profile of a project's criteria (one bar per criterion, height = score)
 * plus the weakest one in text: enough to triage hundreds of projects.
 */
export const ScoreProfile = ({ scores }: { scores: CriterionScoreSummary[] }) => {
  const weakest = scores.reduce((min, s) => (s.score < min.score ? s : min), scores[0]);
  const description = scores.map((s) => `${s.name} ${s.score}`).join(", ");

  return (
    <div className="flex items-center gap-3">
      <span className="flex h-7 items-end gap-0.5" title={description} aria-hidden>
        {scores.map((s) => (
          <span
            key={s.criterionKey}
            className={`w-1.5 rounded-t-sm ${SCORE_BAND_STYLES[scoreBand(s.score)].fill}`}
            style={{ height: `${Math.max(8, s.score)}%` }}
          />
        ))}
      </span>
      <span className="sr-only">Notas por critério: {description}.</span>
      <span className="min-w-0 text-xs leading-tight">
        <span className="block text-fg-muted">Menor nota</span>
        <span className="font-medium">
          {weakest.name} {weakest.score}
        </span>
        <span className="sr-only"> ({SCORE_BAND_LABELS[scoreBand(weakest.score)]})</span>
      </span>
    </div>
  );
};
