import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { FRAMEWORKS, FRAMEWORK_ORDER } from "@/domain/frameworks";
import { FileDropzone } from "@/features/projects/FileDropzone";
import { UploadTable } from "@/features/projects/UploadTable";
import { addFiles, advance, queueSummary } from "@/features/projects/uploadQueue";
import type { UploadItem } from "@/features/projects/uploadQueue";
import { formatFileSize, pluralize } from "@/lib/format";
import { useCreateProject } from "@/services/queries";

const UPLOAD_TICK_MS = 300;

interface NewProjectDialogProps {
  open: boolean;
  onClose: () => void;
}

export const NewProjectDialog = ({ open, onClose }: NewProjectDialogProps) => {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="new-project-title"
      className="m-auto max-h-[calc(100dvh-2rem)] w-[min(72rem,calc(100vw-2rem))] overflow-hidden rounded-[28px] bg-surface p-0 text-fg shadow-[0_24px_64px_rgb(22_22_22/0.25)] backdrop:bg-brand-deep/40 backdrop:backdrop-blur-sm"
    >
      {/* Remount on every open so the form starts empty */}
      {open && <NewProjectForm onDone={onClose} />}
    </dialog>
  );
};

const pillInput =
  "h-12 w-full rounded-full border border-border-strong bg-surface px-4 text-sm leading-5 placeholder:text-fg-muted focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-action aria-invalid:border-danger";

const NewProjectForm = ({ onDone }: { onDone: () => void }) => {
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [freeText, setFreeText] = useState("");
  const [items, setItems] = useState<UploadItem[]>([]);
  const [webSearch, setWebSearch] = useState(true);
  const [submitted, setSubmitted] = useState(false);

  const summary = queueSummary(items);
  const nameMissing = name.trim() === "";
  const materialMissing = items.length === 0 && freeText.trim() === "";

  // MOCK upload: progress advances while any file is still "sending"
  useEffect(() => {
    if (summary.uploading === 0) return;
    const timer = setInterval(() => setItems(advance), UPLOAD_TICK_MS);
    return () => clearInterval(timer);
  }, [summary.uploading]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (nameMissing || materialMissing || summary.uploading > 0) return;
    createProject.mutate(
      { name, company, freeText, webSearch, files: items.map((item) => item.file) },
      { onSuccess: onDone },
    );
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex max-h-[calc(100dvh-2rem)] flex-col">
      <header className="flex items-start justify-between gap-4 border-b border-track px-7 pt-6 pb-[18px]">
        <div className="flex flex-col gap-1">
          <h2 id="new-project-title" className="text-xl font-semibold">
            Novo projeto
          </h2>
          <p className="text-base text-fg-muted">Envie o material do projeto.</p>
        </div>
        <button
          type="button"
          onClick={onDone}
          aria-label="Fechar"
          className="flex shrink-0 items-center justify-center rounded-full border border-border-strong bg-surface p-3 hover:bg-surface-muted"
        >
          <X className="size-6" aria-hidden />
        </button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-[18px] overflow-y-auto px-7 py-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="project-name" className="text-base font-semibold text-fg-soft">
              Nome do projeto <span className="text-action">*</span>
            </label>
            <input
              id="project-name"
              className={pillInput}
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={submitted && nameMissing}
              aria-describedby={submitted && nameMissing ? "project-name-error" : undefined}
              autoFocus
            />
            {submitted && nameMissing && (
              <p id="project-name-error" className="text-xs text-danger">
                Informe o nome do projeto.
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="project-company" className="text-base font-semibold text-fg-soft">
              Equipe ou empresa <span className="font-normal text-fg-muted">(opcional)</span>
            </label>
            <input
              id="project-company"
              className={pillInput}
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="project-free-text" className="text-base font-semibold text-fg-soft">
            Descrição em texto livre <span className="font-normal text-fg-muted">(opcional)</span>
          </label>
          <input
            id="project-free-text"
            className={pillInput}
            placeholder="Problema técnico, o que é novo, o que não se sabia se ia funcionar…"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
          />
        </div>

        <section aria-labelledby="documents-title" className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between gap-4">
            <h3 id="documents-title" className="text-base font-semibold">
              Documentos do projeto
            </h3>
            {summary.count > 0 && (
              <p className="text-xs text-fg-muted">
                {pluralize(summary.count, "arquivo", "arquivos")} · {formatFileSize(summary.bytes)}
              </p>
            )}
          </div>
          <FileDropzone hasFiles={items.length > 0} onFiles={(files) => setItems((current) => addFiles(current, files))} />
          {items.length > 0 && (
            <>
              <UploadTable
                items={items}
                onRemove={(id) => setItems((current) => current.filter((item) => item.id !== id))}
              />
              <p className="text-xs text-fg-muted">
                O tipo é reconhecido pelo nome e pelo conteúdo do arquivo; depoimentos entram como
                evidência de menor peso e são confrontados com os registros.
              </p>
            </>
          )}
        </section>

        <label className="flex cursor-pointer items-start gap-3.5 rounded-2xl border border-track bg-surface px-4 py-3.5">
          <input
            type="checkbox"
            role="switch"
            checked={webSearch}
            onChange={(e) => setWebSearch(e.target.checked)}
            className="peer sr-only"
          />
          <span
            aria-hidden
            className="relative mt-0.5 h-6 w-10 shrink-0 rounded-full bg-border-strong transition-colors peer-checked:bg-action peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-action after:absolute after:top-1/2 after:left-[3px] after:size-[18px] after:-translate-y-1/2 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-4"
          />
          <span className="flex flex-col gap-1">
            <span className="text-base font-semibold">
              Buscar trabalhos similares na web para Novidade e Criatividade
            </span>
            <span className="text-xs leading-[19px] text-fg-secondary">
              Fontes: Google Scholar e arXiv. Antes de rodar, o sistema mostra os termos de busca
              para você aprovar. Nenhum trecho dos documentos é enviado sem essa aprovação. Não
              encontrar similares conta como evidência fraca, nunca como prova de novidade.
            </span>
          </span>
        </label>

        <div className="flex flex-wrap items-center gap-2.5 text-[13px]">
          <span className="font-semibold">Métodos de análise</span>
          {FRAMEWORK_ORDER.map((framework) => (
            <span
              key={framework}
              className="rounded-full border border-border-strong bg-surface px-3 py-1.5 text-fg-secondary"
            >
              {FRAMEWORKS[framework].version}
            </span>
          ))}
          <span className="text-fg-muted">A versão fica registrada no documento de decisão.</span>
        </div>

        {submitted && materialMissing && (
          <p role="alert" className="text-sm text-danger">
            Anexe ao menos um documento ou escreva uma descrição do projeto.
          </p>
        )}
        {createProject.isError && (
          <p role="alert" className="text-sm text-danger">
            Não foi possível enviar o projeto. Tente novamente.
          </p>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-track px-7 pt-4 pb-5">
        <p className="text-[13px] text-fg-muted" aria-live="polite">
          {summary.uploading > 0
            ? `Aguarde o envio de ${pluralize(summary.uploading, "arquivo", "arquivos")} para continuar.`
            : "Campos com * são obrigatórios."}
        </p>
        <div className="flex gap-2.5">
          <button type="button" className="btn-secondary" onClick={onDone}>
            Cancelar
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={createProject.isPending || summary.uploading > 0}
          >
            {createProject.isPending ? "Enviando…" : "Enviar para análise"}
          </button>
        </div>
      </footer>
    </form>
  );
};
