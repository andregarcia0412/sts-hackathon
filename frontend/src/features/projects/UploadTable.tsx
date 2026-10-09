import { X } from "lucide-react";
import { ArticleIcon, CsvIcon, PictureAsPdfIcon } from "@/components/icons/MaterialIcons";
import { extensionOf } from "@/domain/documents";
import { foldRows } from "@/features/projects/uploadQueue";
import type { UploadItem } from "@/features/projects/uploadQueue";
import { formatFileSize } from "@/lib/format";

const FileIcon = ({ name }: { name: string }) => {
  const ext = extensionOf(name);
  const Icon = ext === ".pdf" ? PictureAsPdfIcon : ext === ".csv" ? CsvIcon : ArticleIcon;
  return <Icon className="size-4 shrink-0 text-fg" />;
};

const Status = ({ progress }: { progress: number }) =>
  progress >= 1 ? (
    <span className="text-state-positive-strong">Pronto</span>
  ) : (
    <span className="flex flex-col gap-1">
      <span className="text-fg-secondary">Enviando {Math.round(progress * 100)}%</span>
      <span
        role="progressbar"
        aria-valuenow={Math.round(progress * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="block h-1 w-full rounded-sm bg-surface-sunken"
      >
        <span className="block h-full rounded-sm bg-action" style={{ width: `${progress * 100}%` }} />
      </span>
    </span>
  );

/** Files of the new project: recognized type and upload state; the extra ones fold into one row */
export const UploadTable = ({ items, onRemove }: { items: UploadItem[]; onRemove: (id: string) => void }) => {
  const { visible, rest } = foldRows(items);

  return (
    <div className="overflow-x-auto rounded-2xl border border-track bg-surface">
      <table className="w-full min-w-[640px] table-fixed text-left text-[13px] leading-5">
        <colgroup>
          <col className="w-[46%]" />
          <col className="w-[20%]" />
          <col className="w-[12%]" />
          <col className="w-[16%]" />
          <col className="w-[6%]" />
        </colgroup>
        <thead className="border-b border-divider text-xs font-semibold text-fg-muted">
          <tr>
            <th scope="col" className="py-2.5 pr-3 pl-4">Arquivo</th>
            <th scope="col" className="px-3 py-2.5">Tipo reconhecido</th>
            <th scope="col" className="px-3 py-2.5">Tamanho</th>
            <th scope="col" className="px-3 py-2.5">Situação</th>
            <th scope="col" className="py-2.5 pr-4 pl-1">
              <span className="sr-only">Remover</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-divider">
          {visible.map((item) => (
            <tr key={item.id}>
              <td className="py-2.5 pr-3 pl-4">
                <span className="flex min-w-0 items-start gap-1">
                  <FileIcon name={item.name} />
                  <span className="min-w-0 text-xs leading-4 font-semibold break-all">
                    {item.name}
                  </span>
                </span>
              </td>
              <td className="px-3 py-2.5 text-fg-secondary">{item.kind}</td>
              <td className="px-3 py-2.5 text-fg-muted tabular-nums">{formatFileSize(item.file.size)}</td>
              <td className="px-3 py-2.5">
                <Status progress={item.progress} />
              </td>
              <td className="py-2.5 pr-4 pl-1 text-right">
                <button
                  type="button"
                  className="rounded-full p-1 text-fg-muted hover:bg-surface-sunken hover:text-fg"
                  aria-label={`Remover ${item.name}`}
                  onClick={() => onRemove(item.id)}
                >
                  <X className="size-4" aria-hidden />
                </button>
              </td>
            </tr>
          ))}
          {rest && (
            <tr>
              <td className="py-2.5 pr-3 pl-4 text-fg-secondary">
                + {rest.count} arquivos: {rest.kinds.join(", ")}
              </td>
              <td className="px-3 py-2.5 text-fg-muted">Vários</td>
              <td className="px-3 py-2.5 text-fg-muted tabular-nums">{formatFileSize(rest.bytes)}</td>
              <td className="px-3 py-2.5">
                <Status progress={rest.progress} />
              </td>
              <td />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
