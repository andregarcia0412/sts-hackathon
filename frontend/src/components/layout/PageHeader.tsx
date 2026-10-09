import type { ReactNode } from "react";

interface PageHeaderProps {
  /** Small pill above the title, e.g. "Projeto P1" */
  eyebrow?: ReactNode;
  title: ReactNode;
  /** Line(s) under the title */
  description?: ReactNode;
  /** Right side: status and the screen's main action */
  aside?: ReactNode;
  /** Full-width row under the title (e.g. the list's filters) */
  children?: ReactNode;
}

/** Translucent band under the step header (identification left, action right) */
export const PageHeader = ({ eyebrow, title, description, aside, children }: PageHeaderProps) => (
  <div className="flex shrink-0 flex-col gap-4 border-b border-border bg-white/50 px-4 pt-4 pb-6 sm:px-10 print:hidden">
    <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
      <div className="flex min-w-0 flex-1 basis-96 flex-col items-start gap-4">
        {eyebrow}
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl leading-7 font-semibold text-fg">{title}</h1>
          {description && <div className="text-xs leading-4 text-fg-muted">{description}</div>}
        </div>
      </div>
      {aside && <div className="flex flex-wrap items-end gap-4">{aside}</div>}
    </div>
    {children}
  </div>
);
