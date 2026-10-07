import { BookOpen, ExternalLink } from "lucide-react";
import type { Reference } from "@/domain/types";

export const ReferenceLink = ({ reference }: { reference: Reference }) => {
  return (
    <div className="text-sm">
      {reference.url ? (
        <a
          href={reference.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 font-medium text-accent hover:underline"
        >
          <BookOpen className="size-4 shrink-0" aria-hidden />
          {reference.label}
          <ExternalLink className="size-3.5 shrink-0" aria-hidden />
          <span className="sr-only">(abre em nova aba)</span>
        </a>
      ) : (
        <span className="inline-flex items-center gap-1.5 font-medium">
          <BookOpen className="size-4 shrink-0 text-fg-muted" aria-hidden />
          {reference.label}
        </span>
      )}
      {reference.citation && (
        <blockquote className="mt-1 border-l-2 border-border-strong pl-3 text-fg-muted italic">
          “{reference.citation}”
        </blockquote>
      )}
    </div>
  );
};
