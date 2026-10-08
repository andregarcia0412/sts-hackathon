import { POLARITY_ICONS, POLARITY_STYLES } from "@/components/ui/polarityStyles";
import { SCORE_BAND_ICONS, SCORE_BAND_STYLES } from "@/components/ui/scoreStyles";
import { POLARITY_LABELS } from "@/domain/labels";
import { SCORE_BANDS, SCORE_BAND_LABELS, SCORE_BAND_RANGES } from "@/domain/score";
import type { EvidencePolarity } from "@/domain/types";

const POLARITIES: EvidencePolarity[] = ["positive", "negative"];

export const GraphLegend = () => {
  return (
    <div
      aria-label="Legenda"
      className="space-y-2 rounded-lg border border-border bg-surface/95 p-3 text-xs shadow-sm"
    >
      <div>
        <p className="mb-1 font-semibold">Força da evidência</p>
        <ul className="space-y-0.5">
          {SCORE_BANDS.map((band) => {
            const Icon = SCORE_BAND_ICONS[band];
            return (
              <li key={band} className={`flex items-center gap-1.5 ${SCORE_BAND_STYLES[band].text}`}>
                <Icon className="size-3.5" aria-hidden />
                <span className="text-fg">
                  {SCORE_BAND_LABELS[band]}{" "}
                  <span className="text-fg-muted">({SCORE_BAND_RANGES[band]})</span>
                </span>
              </li>
            );
          })}
        </ul>
      </div>
      <div>
        <p className="mb-1 font-semibold">Evidência</p>
        <ul className="space-y-0.5">
          {POLARITIES.map((polarity) => {
            const Icon = POLARITY_ICONS[polarity];
            return (
              <li key={polarity} className="flex items-center gap-1.5">
                <Icon className={`size-3.5 ${POLARITY_STYLES[polarity].text}`} aria-hidden />
                {POLARITY_LABELS[polarity]}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
};
