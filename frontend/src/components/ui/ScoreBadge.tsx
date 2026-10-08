import { SCORE_BAND_ICONS, SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { SCORE_BAND_LABELS, scoreBand } from "@/domain/score";

interface ScoreBadgeProps {
  score: number;
  /** Show the band label ("Evidência forte") next to the number */
  showLabel?: boolean;
  size?: "sm" | "md";
}

export const ScoreBadge = ({
  score,
  showLabel = false,
  size = "md",
}: ScoreBadgeProps) => {
  const band = scoreBand(score);
  const styles = SCORE_BAND_STYLES[band];
  const Icon = SCORE_BAND_ICONS[band];
  const label = SCORE_BAND_LABELS[band];

  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full font-medium tabular-nums ${styles.soft} ${styles.text} ${
        size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-0.5 text-sm"
      }`}
      title={`Força da evidência: ${score}/100 (${label})`}
    >
      <Icon className={size === "sm" ? "size-3.5" : "size-4"} aria-hidden />
      <span>{score}</span>
      {showLabel ? (
        <span className="font-normal">· {label}</span>
      ) : (
        <span className="sr-only">({label})</span>
      )}
    </span>
  );
};
