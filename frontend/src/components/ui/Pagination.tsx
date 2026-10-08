import { KeyboardArrowRightIcon } from "@/components/icons/MaterialIcons";

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

const arrowClass =
  "flex size-9 items-center justify-center rounded-full text-fg-secondary transition-colors hover:bg-surface-sunken disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent";

export const Pagination = ({ page, pageSize, total, onChange }: PaginationProps) => {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);

  return (
    <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-fg-muted">
        Mostrando <span className="font-semibold text-fg tabular-nums">{first}–{last}</span> de{" "}
        <span className="font-semibold text-fg tabular-nums">{total}</span>
      </p>
      {pageCount > 1 && (
        <ul className="flex items-center gap-1">
          <li>
            <button
              type="button"
              className={arrowClass}
              disabled={page <= 1}
              onClick={() => onChange(page - 1)}
              aria-label="Página anterior"
            >
              <KeyboardArrowRightIcon className="size-6 rotate-180" />
            </button>
          </li>
          {visiblePages(page, pageCount).map((p, i) =>
            p === "gap" ? (
              <li key={`gap-${i}`} className="px-1 text-fg-muted" aria-hidden>
                …
              </li>
            ) : (
              <li key={p}>
                <button
                  type="button"
                  aria-current={p === page ? "page" : undefined}
                  onClick={() => onChange(p)}
                  className={`flex size-9 items-center justify-center rounded-full font-semibold tabular-nums transition-colors ${
                    p === page ? "bg-action text-white" : "text-fg-secondary hover:bg-surface-sunken"
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
              className={arrowClass}
              disabled={page >= pageCount}
              onClick={() => onChange(page + 1)}
              aria-label="Próxima página"
            >
              <KeyboardArrowRightIcon className="size-6" />
            </button>
          </li>
        </ul>
      )}
    </nav>
  );
};
