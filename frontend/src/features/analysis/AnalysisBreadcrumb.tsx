import { ChevronRight } from "lucide-react";
import { FRAMEWORK_LABELS } from "@/domain/labels";
import { getNodePath, getNodeTitle } from "@/domain/tree";
import type { Framework } from "@/domain/types";
import type { AnalysisExplorer } from "@/features/analysis/useAnalysisExplorer";

interface AnalysisBreadcrumbProps {
  explorer: AnalysisExplorer;
  framework: Framework;
}

/** Frascati › 3. Incerteza › 3.1 PROJ-13 › 3.1.1 Evidência: each level goes up to that node */
export const AnalysisBreadcrumb = ({
  explorer,
  framework,
}: AnalysisBreadcrumbProps) => {
  const path = explorer.selectedId
    ? getNodePath(explorer.index, explorer.selectedId)
    : [];

  return (
    <nav aria-label="Caminho do item selecionado" className="min-w-0">
      <ol className="flex min-w-0 items-center gap-1 text-sm">
        <li className="shrink-0">
          <button
            type="button"
            className="btn-ghost px-1.5 py-1 font-semibold text-fg"
            onClick={() => explorer.select(null)}
            title="Conjunto de critérios em uso"
          >
            {FRAMEWORK_LABELS[framework]}
          </button>
        </li>
        {path.map((node, i) => {
          const isLast = i === path.length - 1;
          return (
            <li key={node.id} className="flex min-w-0 items-center gap-1">
              <ChevronRight className="size-4 shrink-0 text-fg-muted" aria-hidden />
              <button
                type="button"
                aria-current={isLast ? "location" : undefined}
                className={`btn-ghost min-w-0 px-1.5 py-1 ${isLast ? "text-fg" : ""}`}
                onClick={() => explorer.select(node.id)}
                title={getNodeTitle(node)}
              >
                <span className="truncate">
                  {node.number}. {getNodeTitle(node)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
