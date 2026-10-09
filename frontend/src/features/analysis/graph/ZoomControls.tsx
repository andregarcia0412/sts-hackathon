import { useReactFlow } from "@xyflow/react";
import { AddIcon, CheckIndeterminateIcon, FullscreenIcon } from "@/components/icons/MaterialIcons";

const buttonClass =
  "flex size-6 items-center justify-center rounded text-fg-secondary transition-colors hover:bg-surface hover:text-fg";

/** Zoom out / in / frame everything, stacked in the top-left corner as in the design */
export const ZoomControls = ({ onFit }: { onFit: () => void }) => {
  const { zoomIn, zoomOut } = useReactFlow();
  return (
    <div role="group" aria-label="Controles da árvore" className="flex flex-col gap-1 rounded-lg bg-surface-sunken p-1">
      <button type="button" className={buttonClass} aria-label="Afastar" onClick={() => zoomOut({ duration: 200 })}>
        <CheckIndeterminateIcon className="size-4" />
      </button>
      <button type="button" className={buttonClass} aria-label="Aproximar" onClick={() => zoomIn({ duration: 200 })}>
        <AddIcon className="size-4" />
      </button>
      <button type="button" className={buttonClass} aria-label="Enquadrar a árvore inteira" onClick={onFit}>
        <FullscreenIcon className="size-4" />
      </button>
    </div>
  );
};
