import { CircleMinus, CirclePlus, Equal, Flag, SlidersHorizontal } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { SCORE_BAND_LABELS, SCORE_MAX, scoreBand } from "@/domain/score";
import type { ScoreExplanation, ScoreFactor } from "@/domain/types";
import { formatPercent, formatPoints, formatScore } from "@/lib/scoreFormat";

/*
 * Waterfall that explains a score: start point → each factor up or down →
 * final score. Scale 0–100. Every step carries a signed value and an icon,
 * so polarity never depends on color alone (green/red is weak for deutan).
 */

/** A factor plus how to show and open it (the caller knows the tree numbering) */
export interface BreakdownFactor extends ScoreFactor {
  number?: string;
  onSelect?: () => void;
}

interface ScoreBreakdownProps {
  explanation: ScoreExplanation;
  factors: BreakdownFactor[];
  score: number;
  /** With its article, used in the labels: "da regra", "do critério" */
  subject: string;
}

const pct = (value: number) => `${(Math.max(0, Math.min(SCORE_MAX, value)) / SCORE_MAX) * 100}%`;

const Bar = ({ from, to, className }: { from: number; to: number; className: string }) => {
  const left = Math.min(from, to);
  const width = Math.abs(to - from);
  return (
    <span
      className={`absolute top-1/2 h-3 -translate-y-1/2 rounded ${className}`}
      style={{ left: pct(left), width: `max(${pct(width)}, 3px)` }}
    />
  );
};

const factorStyle = (factor: ScoreFactor): { Icon: LucideIcon; bar: string; icon: string } => {
  if (factor.kind === "adjustment") {
    return { Icon: SlidersHorizontal, bar: "bg-fg-muted/60", icon: "text-fg-muted" };
  }
  if (factor.kind === "rule") {
    const band = scoreBand(factor.value ?? 0);
    return { Icon: Flag, bar: SCORE_BAND_STYLES[band].fill, icon: SCORE_BAND_STYLES[band].text };
  }
  return factor.points >= 0
    ? { Icon: CirclePlus, bar: "bg-evidence-positive", icon: "text-evidence-positive" }
    : { Icon: CircleMinus, bar: "bg-evidence-negative", icon: "text-evidence-negative" };
};

const Row = ({
  label,
  detail,
  value,
  icon,
  onSelect,
  title,
  children,
}: {
  label: string;
  detail?: string;
  value: string;
  icon: ReactNode;
  onSelect?: () => void;
  title: string;
  children: ReactNode;
}) => (
  <li className="grid grid-cols-[minmax(0,1fr)_3rem] items-center gap-x-2 py-1" title={title}>
    {/* Label on its own line: the panel is narrow and labels must not be cut */}
    <span className="col-span-2 flex min-w-0 items-start gap-1.5">
      {icon}
      {onSelect ? (
        <button type="button" onClick={onSelect} className="text-left hover:text-accent hover:underline">
          {label}
        </button>
      ) : (
        <span>{label}</span>
      )}
      {detail && <span className="shrink-0 text-fg-muted">· {detail}</span>}
    </span>
    <span className="relative ml-5 h-4" aria-hidden>
      {/* hairline grid at 0, 50, 100 */}
      <span className="absolute inset-y-0 left-0 w-px bg-border" />
      <span className="absolute inset-y-0 left-1/2 w-px bg-border" />
      <span className="absolute inset-y-0 right-0 w-px bg-border" />
      {children}
    </span>
    <span className="text-right font-medium tabular-nums">{value}</span>
  </li>
);

export const ScoreBreakdown = ({ explanation, factors, score, subject }: ScoreBreakdownProps) => {
  // Cumulative steps of the waterfall: each factor goes from → to
  const steps = factors.reduce<{ factor: BreakdownFactor; from: number; to: number }[]>(
    (acc, factor) => {
      const from = acc.at(-1)?.to ?? explanation.baseline;
      return [...acc, { factor, from, to: from + factor.points }];
    },
    [],
  );
  const band = scoreBand(score);

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs text-fg-muted">{explanation.method}</figcaption>
      <ol className="text-xs" aria-label={`Composição da nota ${subject}`}>
        {explanation.baseline > 0 && (
          <Row
            label="Ponto de partida (neutro)"
            value={formatScore(explanation.baseline)}
            icon={<span className="size-3.5 shrink-0" />}
            title={`Ponto de partida: ${explanation.baseline}`}
          >
            <Bar from={0} to={explanation.baseline} className="bg-border-strong" />
          </Row>
        )}
        {steps.map(({ factor, from, to }, i) => {
          const { Icon, bar, icon } = factorStyle(factor);
          const detail =
            factor.kind === "rule" && factor.value !== undefined && factor.weight !== undefined
              ? `${factor.value} × ${formatPercent(factor.weight)}`
              : undefined;
          const label = factor.number ? `${factor.number} ${factor.label}` : factor.label;
          return (
            <Row
              key={factor.refId ?? `adj-${i}`}
              label={label}
              detail={detail}
              value={formatPoints(factor.points)}
              icon={<Icon className={`mt-px size-3.5 shrink-0 ${icon}`} aria-hidden />}
              onSelect={factor.onSelect}
              title={`${label}: ${formatPoints(factor.points)} pontos (de ${formatScore(from)} para ${formatScore(to)})`}
            >
              <Bar from={from} to={to} className={bar} />
            </Row>
          );
        })}
        <li className="mt-1 border-t border-border pt-1">
          <ol>
            <Row
              label={`Nota ${subject}`}
              detail={SCORE_BAND_LABELS[band].toLowerCase()}
              value={formatScore(score)}
              icon={<Equal className="size-3.5 shrink-0 text-fg-muted" aria-hidden />}
              title={`Nota final: ${score} (${SCORE_BAND_LABELS[band]})`}
            >
              <Bar from={0} to={score} className={SCORE_BAND_STYLES[band].fill} />
            </Row>
          </ol>
        </li>
      </ol>
      <p className="text-[11px] text-fg-muted italic">
        Explicação ilustrativa: o cálculo definitivo da nota ainda está em definição.
      </p>
    </figure>
  );
};
