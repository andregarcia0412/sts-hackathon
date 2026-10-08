import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { FileDropzone } from "@/features/projects/FileDropzone";
import { useCreateProject } from "@/services/queries";

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
      className="m-auto w-[min(40rem,calc(100vw-2rem))] rounded-2xl bg-surface p-0 text-fg shadow-xl backdrop:bg-brand-deep/40 backdrop:backdrop-blur-sm"
    >
      {/* Remount on every open so the form starts empty */}
      {open && <NewProjectForm onDone={onClose} />}
    </dialog>
  );
};

const NewProjectForm = ({ onDone }: { onDone: () => void }) => {
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [freeText, setFreeText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const nameMissing = name.trim() === "";
  const materialMissing = files.length === 0 && freeText.trim() === "";

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (nameMissing || materialMissing) return;
    createProject.mutate(
      { name, company, freeText, files },
      { onSuccess: onDone },
    );
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <header className="flex items-start justify-between gap-4 border-b border-border px-6 pt-6 pb-4">
        <div className="flex flex-col gap-1">
          <p className="caps-label text-accent">Upload de arquivos</p>
          <h2 id="new-project-title" className="text-xl leading-6 font-semibold">
            Novo projeto
          </h2>
          <p className="text-sm leading-5 text-fg-muted">
            Envie os documentos do projeto, descreva-o em texto livre, ou os
            dois.
          </p>
        </div>
        <button
          type="button"
          className="btn-ghost p-2"
          aria-label="Fechar"
          onClick={onDone}
        >
          <X className="size-5" aria-hidden />
        </button>
      </header>

      <div className="flex max-h-[70dvh] flex-col gap-5 overflow-y-auto px-6 py-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="project-name" className="label">
              Nome do projeto <span className="text-action">*</span>
            </label>
            <input
              id="project-name"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={submitted && nameMissing}
              aria-describedby={
                submitted && nameMissing ? "project-name-error" : undefined
              }
              autoFocus
            />
            {submitted && nameMissing && (
              <p id="project-name-error" className="mt-1.5 text-xs text-danger">
                Informe o nome do projeto.
              </p>
            )}
          </div>
          <div>
            <label htmlFor="project-company" className="label">
              Empresa <span className="font-normal text-fg-muted">(opcional)</span>
            </label>
            <input
              id="project-company"
              className="input"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
        </div>

        <fieldset>
          <legend className="label">Documentos do projeto</legend>
          <FileDropzone files={files} onChange={setFiles} />
        </fieldset>

        <div>
          <label htmlFor="project-free-text" className="label">
            Descrição em texto livre
          </label>
          <textarea
            id="project-free-text"
            className="input min-h-28 resize-y"
            placeholder="Descreva o projeto: o problema técnico, o que é novo, o que ainda não se sabe se vai funcionar…"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
          />
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

      <footer className="flex flex-wrap justify-end gap-3 border-t border-border px-6 py-4">
        <button type="button" className="btn-secondary" onClick={onDone}>
          Cancelar
        </button>
        <button
          type="submit"
          className="btn-primary"
          disabled={createProject.isPending}
        >
          {createProject.isPending ? "Enviando…" : "Enviar para análise"}
        </button>
      </footer>
    </form>
  );
};
