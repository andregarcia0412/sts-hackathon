import { CloudUpload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { ArticleIcon } from "@/components/icons/MaterialIcons";
import { MAX_FILE_BYTES } from "@/domain/documents";
import type { ProjectSummary } from "@/domain/types";
import { formatFileSize } from "@/lib/format";
import { useResendDocument } from "@/services/queries";

interface ResendFileDialogProps {
  /** Project waiting for a new version of the unreadable file; null = closed */
  project: ProjectSummary | null;
  onClose: () => void;
}

/** "Reenviar arquivo": replaces the file that could not be read */
export const ResendFileDialog = ({ project, onClose }: ResendFileDialogProps) => {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (project && !dialog.open) dialog.showModal();
    if (!project && dialog.open) dialog.close();
  }, [project]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="resend-title"
      className="m-auto w-[min(36rem,calc(100vw-2rem))] rounded-3xl bg-surface p-0 text-fg shadow-xl backdrop:bg-brand-deep/40 backdrop:backdrop-blur-sm"
    >
      {project && <ResendForm key={project.id} project={project} onDone={onClose} />}
    </dialog>
  );
};

const ResendForm = ({ project, onDone }: { project: ProjectSummary; onDone: () => void }) => {
  const resend = useResendDocument();
  const [file, setFile] = useState<File | null>(null);
  const [rejected, setRejected] = useState(false);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    // Any document type: the back-end identifies files by content and flags
    // unknown kinds instead of rejecting them (see FileDropzone).
    maxSize: MAX_FILE_BYTES,
    multiple: false,
    onDrop: (accepted, rejections) => {
      setRejected(rejections.length > 0);
      if (accepted[0]) setFile(accepted[0]);
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (file) resend.mutate({ projectId: project.id, file }, { onSuccess: onDone });
      }}
    >
      <header className="flex items-start justify-between gap-4 border-b border-border px-7 pt-7 pb-5">
        <div className="flex flex-col gap-1">
          <h2 id="resend-title" className="text-xl leading-6 font-semibold">
            Reenviar arquivo
          </h2>
          <p className="text-sm leading-5 text-fg-muted">
            {project.readError ? (
              <>
                <strong className="font-semibold text-fg">{project.readError.fileName}</strong> não pôde
                ser lido.
              </>
            ) : (
              "Um arquivo deste projeto não pôde ser lido."
            )}{" "}
            Envie uma nova versão (de preferência com texto selecionável) e a análise recomeça.
          </p>
        </div>
        <button
          type="button"
          onClick={onDone}
          aria-label="Fechar"
          className="flex size-12 shrink-0 items-center justify-center rounded-full border border-border-strong hover:bg-surface-muted"
        >
          <X className="size-6" aria-hidden />
        </button>
      </header>

      <div className="flex flex-col gap-3 px-7 py-5">
        <div
          {...getRootProps({
            className: `flex cursor-pointer flex-col items-center gap-2 rounded-2xl border border-dashed px-4 py-6 text-center transition-colors ${
              isDragActive ? "border-action bg-accent-soft" : "border-action hover:bg-accent-soft/60"
            }`,
          })}
        >
          <input {...getInputProps()} aria-label="Selecionar o novo arquivo" />
          <span className="flex size-12 items-center justify-center rounded-full bg-brand-blush text-accent">
            <CloudUpload className="size-6" aria-hidden />
          </span>
          <p className="text-base leading-5 font-semibold">Arraste o arquivo ou clique para selecionar</p>
          <p className="text-xs text-fg-muted">Um arquivo · até {formatFileSize(MAX_FILE_BYTES)}</p>
        </div>
        {rejected && (
          <p role="alert" className="text-xs text-danger">
            Formato não aceito ou arquivo maior que o limite.
          </p>
        )}
        {file && (
          <p className="flex items-center gap-2 rounded-xl bg-surface-muted px-3 py-2 text-sm">
            <ArticleIcon className="size-4 shrink-0 text-fg-secondary" />
            <span className="min-w-0 flex-1 font-semibold break-all">{file.name}</span>
            <span className="text-xs text-fg-muted tabular-nums">{formatFileSize(file.size)}</span>
          </p>
        )}
        {resend.isError && (
          <p role="alert" className="text-sm text-danger">
            Não foi possível reenviar. Tente novamente.
          </p>
        )}
      </div>

      <footer className="flex justify-end gap-3 border-t border-border px-7 py-5">
        <button type="button" className="btn-secondary" onClick={onDone}>
          Cancelar
        </button>
        <button type="submit" className="btn-primary" disabled={!file || resend.isPending}>
          {resend.isPending ? "Reenviando…" : "Reenviar e analisar"}
        </button>
      </footer>
    </form>
  );
};
