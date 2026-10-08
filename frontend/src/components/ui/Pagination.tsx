import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

/** Page numbers to show: first, last, current ±1, with gaps ("…") */
const visiblePages = (page: number, pageCount: number): (number | "gap")[] => {
  const pages = new Set([1, pageCount, page - 1, page, page + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= pageCount).sort((a, b) => a - b);
  return sorted.flatMap((p, i) => (i > 0 && p - sorted[i - 1] > 1 ? ["gap" as const, p] : [p]));
};

export const Pagination = ({ page, pageSize, total, onChange }: PaginationProps) => {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);

  return (
    <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-fg-muted">
        Mostrando <span className="font-medium text-fg tabular-nums">{first}–{last}</span> de{" "}
        <span className="font-medium text-fg tabular-nums">{total}</span>
      </p>
      {pageCount > 1 && (
        <ul className="flex items-center gap-1">
          <li>
            <button
              type="button"
              className="btn-ghost px-2"
              disabled={page <= 1}
              onClick={() => onChange(page - 1)}
              aria-label="Página anterior"
            >
              <ChevronLeft className="size-4" aria-hidden />
            </button>
          </li>
          {visiblePages(page, pageCount).map((p, i) =>
            p === "gap" ? (
              <li key={`gap-${i}`} className="px-1 text-fg-muted" aria-hidden>…</li>
            ) : (
              <li key={p}>
                <button
                  type="button"
                  aria-current={p === page ? "page" : undefined}
                  onClick={() => onChange(p)}
                  className={`min-w-8 rounded-md px-2 py-1 tabular-nums ${
                    p === page ? "bg-accent text-accent-fg" : "hover:bg-surface-muted"
                  }`}
                >
                  {p}
                </button>
              </li>
            ),
          )}
          <li>
            <button
              type="button"
              className="btn-ghost px-2"
              disabled={page >= pageCount}
              onClick={() => onChange(page + 1)}
              aria-label="Próxima página"
            >
              <ChevronRight className="size-4" aria-hidden />
            </button>
          </li>
        </ul>
      )}
    </nav>
  );
};
