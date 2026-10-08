import { Search } from "lucide-react";
import { useEffect, useEffectEvent, useState } from "react";

const SEARCH_DEBOUNCE_MS = 300;

/** Pill search box; the list (and the URL) only change when typing pauses */
export const ProjectSearch = ({
  value,
  onSearch,
}: {
  value: string;
  onSearch: (search: string) => void;
}) => {
  const [draft, setDraft] = useState(value);

  const onTypingPause = useEffectEvent(() => {
    if (draft !== value) onSearch(draft);
  });
  useEffect(() => {
    const timer = setTimeout(onTypingPause, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [draft]);

  // "Limpar filtros" clears the URL: follow it (state adjusted during render)
  const [lastValue, setLastValue] = useState(value);
  if (value !== lastValue) {
    setLastValue(value);
    if (value === "") setDraft("");
  }

  return (
    <div role="search" className="relative w-full sm:w-auto sm:max-w-[345px] sm:min-w-[17.75rem] sm:flex-1">
      <label htmlFor="project-search" className="sr-only">
        Buscar projeto, equipe ou código
      </label>
      <input
        id="project-search"
        type="search"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Buscar projeto, equipe ou código"
        className="h-12 w-full rounded-full border border-fg-faint bg-surface py-2 pr-12 pl-4 text-sm placeholder:text-fg-subtle focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-action"
      />
      <Search className="pointer-events-none absolute top-1/2 right-4 size-5 -translate-y-1/2 text-fg-secondary" aria-hidden />
    </div>
  );
};
