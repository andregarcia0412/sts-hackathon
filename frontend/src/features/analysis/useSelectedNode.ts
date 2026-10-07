import { useSearchParams } from "react-router-dom";
import { SELECTED_NODE_PARAM } from "@/routes/paths";

/**
 * The selected node lives in the URL (?no=crit-x.rule-y.ev-z), so back/forward
 * work and a link can point straight at a piece of evidence. Every other part
 * of the analysis screen reacts to this single source of truth.
 */
export const useSelectedNode = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get(SELECTED_NODE_PARAM);

  const select = (nodeId: string | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (nodeId) next.set(SELECTED_NODE_PARAM, nodeId);
      else next.delete(SELECTED_NODE_PARAM);
      return next;
    });
  };

  return { selectedId, select };
};
