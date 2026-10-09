import { ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { CsvIcon, PictureAsPdfIcon } from "@/components/icons/MaterialIcons";

interface ExportMenuProps {
  onPdf: () => void;
  onCsv: () => void;
  csvPending?: boolean;
  /** Set when the last CSV export failed */
  error?: string;
  /** Opens above the button, as wide as it (bottom of the side panel) */
  openUp?: boolean;
  className?: string;
}

/** "Exportar": the full document as PDF or the decision as a spreadsheet (CSV) */
export const ExportMenu = ({ onPdf, onCsv, csvPending, error, openUp, className = "" }: ExportMenuProps) => {
  const id = useId();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemsRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside; the first option takes the focus
  useEffect(() => {
    if (!open) return;
    itemsRef.current?.querySelector("button")?.focus();
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  const close = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const items = [...(itemsRef.current?.querySelectorAll("button") ?? [])];
    const current = items.indexOf(document.activeElement as HTMLButtonElement);
    const step = event.key === "ArrowDown" ? 1 : -1;
    items.at((current + step) % items.length)?.focus();
  };

  const choose = (action: () => void) => {
    close();
    action();
  };

  return (
    <div ref={rootRef} className={`relative ${className}`} onKeyDown={open ? onKeyDown : undefined}>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-controls={`${id}-opcoes`}
        onClick={() => setOpen(!open)}
        disabled={csvPending}
        className="btn-primary w-full"
      >
        {csvPending ? "Exportando…" : "Exportar"}
        <ChevronDown
          className={`size-5 shrink-0 transition-transform duration-200 ${open !== !!openUp ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      {open && (
        <div
          ref={itemsRef}
          id={`${id}-opcoes`}
          className={`absolute z-30 flex flex-col gap-0.5 rounded-2xl border border-border bg-surface p-1.5 shadow-[0_12px_32px_rgb(22_22_22/0.16)] animate-dropdown-in ${
            // Side panel: as wide as the button, so its scroll box never cuts it
            openUp ? "inset-x-0 bottom-full mb-2" : "top-full right-0 mt-2 w-64"
          }`}
        >
          <ExportOption icon={<PictureAsPdfIcon className="size-6" />} label="PDF" hint="Documento completo, para arquivar" onClick={() => choose(onPdf)} />
          <ExportOption icon={<CsvIcon className="size-6" />} label="CSV" hint="Planilha com a decisão e os critérios" onClick={() => choose(onCsv)} />
        </div>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
};

interface ExportOptionProps {
  icon: ReactNode;
  label: string;
  hint: string;
  onClick: () => void;
}

const ExportOption = ({ icon, label, hint, onClick }: ExportOptionProps) => (
  <button
    type="button"
    onClick={onClick}
    className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-left outline-none hover:bg-accent-soft focus-visible:bg-accent-soft"
  >
    <span className="text-action">{icon}</span>
    <span className="flex flex-col">
      <span className="text-sm leading-5 font-semibold text-fg">{label}</span>
      <span className="text-xs leading-4 text-fg-muted">{hint}</span>
    </span>
  </button>
);
