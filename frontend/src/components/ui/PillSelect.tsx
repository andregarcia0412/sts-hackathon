import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";

export interface PillSelectOption<T extends string> {
  value: T;
  label: string;
  /** Small note next to the option in the list (e.g. "sugestão do sistema") */
  hint?: string;
}

interface PillSelectProps<T extends string> {
  /** Accessible name ("Decisão"); read together with the current value */
  label: string;
  options: PillSelectOption<T>[];
  value: T | undefined;
  onChange: (value: T | undefined) => void;
  /** Text on the control when nothing is chosen; also the "no filter" option */
  placeholder?: string;
  /** Text on the control for the chosen option (defaults to its label) */
  display?: (option: PillSelectOption<T>) => string;
  /** Wine border when it is filtering something */
  highlighted?: boolean;
  /** Draws the chosen option on the control and in the list (default: its label) */
  renderOption?: (option: PillSelectOption<T>) => ReactNode;
  /** The placeholder is only a prompt, not a choice (e.g. a required rating) */
  allowEmpty?: boolean;
  /** Open the list upwards (control near the bottom of the screen) */
  openUp?: boolean;
  className?: string;
}

/**
 * Pill dropdown with the brand's look (the native select list cannot be
 * styled). Select-only combobox pattern: focus stays on the control, arrows
 * move, Enter/Space choose, Escape closes; the control sizes to its text.
 */
export const PillSelect = <T extends string>({
  label,
  options,
  value,
  onChange,
  placeholder,
  display = (option) => option.label,
  highlighted = false,
  renderOption,
  allowEmpty = true,
  openUp = false,
  className = "",
}: PillSelectProps<T>) => {
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  // "No filter" first when there is a placeholder
  const items: { value: T | undefined; label: string; hint?: string; option?: PillSelectOption<T> }[] = [
    ...(placeholder && allowEmpty ? [{ value: undefined, label: placeholder }] : []),
    ...options.map((option) => ({ ...option, option })),
  ];
  const selectedIndex = Math.max(0, items.findIndex((item) => item.value === value));
  const [active, setActive] = useState(selectedIndex);
  const chosen = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Keep the highlighted option visible in long lists (scrolls the list only)
  useEffect(() => {
    const option = open ? document.getElementById(`${id}-opcao-${active}`) : null;
    const list = option?.parentElement;
    if (!option || !list) return;
    if (option.offsetTop < list.scrollTop) list.scrollTop = option.offsetTop;
    else if (option.offsetTop + option.offsetHeight > list.scrollTop + list.clientHeight) {
      list.scrollTop = option.offsetTop + option.offsetHeight - list.clientHeight;
    }
  }, [open, active, id]);

  const openList = () => {
    setActive(selectedIndex);
    setOpen(true);
  };

  const choose = (index: number) => {
    onChange(items[index].value);
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    const last = items.length - 1;
    const keys: Record<string, () => void> = open
      ? {
          ArrowDown: () => setActive(Math.min(last, active + 1)),
          ArrowUp: () => setActive(Math.max(0, active - 1)),
          Home: () => setActive(0),
          End: () => setActive(last),
          Enter: () => choose(active),
          " ": () => choose(active),
          Escape: () => setOpen(false),
        }
      : { ArrowDown: openList, ArrowUp: openList, Enter: openList, " ": openList };
    const action = keys[event.key];
    if (action) {
      event.preventDefault();
      action();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <span id={`${id}-rotulo`} className="sr-only">
        {label}
      </span>
      <button
        type="button"
        role="combobox"
        aria-labelledby={`${id}-rotulo ${id}-valor`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-lista`}
        aria-activedescendant={open ? `${id}-opcao-${active}` : undefined}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onKeyDown}
        className={`flex h-12 w-full items-center justify-between gap-3 rounded-full border bg-surface pr-3 pl-4 text-left text-base leading-5 whitespace-nowrap transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-action ${
          highlighted || open ? "border-action" : "border-border-strong"
        }`}
      >
        <span id={`${id}-valor`} className="flex min-w-0 items-center">
          {chosen ? (
            renderOption ? renderOption(chosen) : display(chosen)
          ) : (
            <span className={allowEmpty ? "" : "text-fg-muted"}>{placeholder}</span>
          )}
        </span>
        <ChevronDown
          className={`size-5 shrink-0 text-fg-secondary transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      {open && (
        <ul
          id={`${id}-lista`}
          role="listbox"
          aria-labelledby={`${id}-rotulo`}
          className={`absolute left-0 z-30 flex ${openUp ? "bottom-full mb-2" : "top-full mt-2"}  max-h-80 min-w-full flex-col gap-0.5 overflow-y-auto rounded-2xl border border-border bg-surface p-1.5 shadow-[0_12px_32px_rgb(22_22_22/0.16)] animate-dropdown-in`}
        >
          {items.map((item, index) => {
            const selected = item.value === value;
            return (
              <li
                key={item.label}
                id={`${id}-opcao-${index}`}
                role="option"
                aria-selected={selected}
                onPointerMove={() => setActive(index)}
                onClick={() => choose(index)}
                className={`flex cursor-pointer items-center justify-between gap-4 rounded-xl px-3 py-2.5 text-sm leading-5 whitespace-nowrap ${
                  index === active ? "bg-accent-soft" : ""
                } ${selected ? "font-semibold text-accent" : item.value === undefined ? "text-fg-muted" : "text-fg"}`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  {item.option && renderOption ? renderOption(item.option) : item.label}
                  {item.hint && <span className="text-xs font-normal text-fg-muted">{item.hint}</span>}
                </span>
                <Check className={`size-4 shrink-0 ${selected ? "" : "invisible"}`} aria-hidden />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
