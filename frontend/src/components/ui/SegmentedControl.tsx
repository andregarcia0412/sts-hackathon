interface SegmentedControlProps<T extends string> {
  label: string;
  options: { value: T; label: string; title?: string }[];
  value: T;
  onChange: (value: T) => void;
}

/** Pill toggle ("Critério | Mapa geral", methods): one option pressed at a time */
export const SegmentedControl = <T extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) => (
  <div role="group" aria-label={label} className="flex rounded-full bg-surface-sunken p-1">
    {options.map((option) => (
      <button
        key={option.value}
        type="button"
        aria-pressed={option.value === value}
        title={option.title}
        onClick={() => onChange(option.value)}
        className={`rounded-full px-3 py-1.5 text-xs leading-4 font-semibold whitespace-nowrap transition-colors ${
          option.value === value
            ? "bg-surface text-fg shadow-card"
            : "text-fg-muted hover:text-fg"
        }`}
      >
        {option.label}
      </button>
    ))}
  </div>
);
