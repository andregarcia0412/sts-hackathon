import { CalendarDays } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { formatDate } from "@/lib/format";

interface DateRangeFieldProps {
  from?: string;
  to?: string;
  onChange: (range: { from?: string; to?: string }) => void;
}

/** "YYYY-MM-DD" → "01/09/26" (the day itself, no time zone shift) */
const show = (day: string) => formatDate(`${day}T12:00:00`).replace(/\/(\d{2})(\d{2})$/, "/$2");

/** "Data de envio": one pill that opens a "de / até" period */
export const DateRangeField = ({ from, to, onChange }: DateRangeFieldProps) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside or pressing Escape
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const label =
    from || to ? `${from ? show(from) : "…"} – ${to ? show(to) : "…"}` : "Data de envio";

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen(!open)}
        className={`flex h-12 w-full items-center justify-between gap-3 rounded-full border bg-surface pr-3 pl-4 text-left text-base whitespace-nowrap sm:w-52 ${
          from || to ? "border-action" : "border-border-strong"
        }`}
      >
        <span className="truncate">{label}</span>
        <CalendarDays className="size-5 shrink-0 text-fg-secondary" aria-hidden />
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Período de envio"
          className="absolute top-full left-0 z-20 mt-2 flex w-72 flex-col gap-3 rounded-2xl border border-border bg-surface p-4 shadow-[0_12px_32px_rgb(22_22_22/0.18)]"
        >
          <label className="field-label mb-0 flex flex-col gap-1">
            Enviado a partir de
            <input
              type="date"
              className="input rounded-full py-2 text-sm"
              value={from ?? ""}
              max={to}
              onChange={(e) => onChange({ from: e.target.value || undefined, to })}
            />
          </label>
          <label className="field-label mb-0 flex flex-col gap-1">
            Enviado até
            <input
              type="date"
              className="input rounded-full py-2 text-sm"
              value={to ?? ""}
              min={from}
              onChange={(e) => onChange({ from, to: e.target.value || undefined })}
            />
          </label>
          <div className="flex justify-between">
            <button
              type="button"
              className="btn-link text-fg-secondary"
              disabled={!from && !to}
              onClick={() => onChange({})}
            >
              Limpar período
            </button>
            <button type="button" className="btn-link" onClick={() => setOpen(false)}>
              Fechar
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
