import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { FRAMEWORKS, FRAMEWORK_ORDER } from "@/domain/frameworks";
import { FileDropzone } from "@/features/projects/FileDropzone";
import { UploadTable } from "@/features/projects/UploadTable";
import { addFiles, advance, queueSummary } from "@/features/projects/uploadQueue";
import type { UploadItem } from "@/features/projects/uploadQueue";
import { formatFileSize, pluralize } from "@/lib/format";
import { paths } from "@/routes/paths";
import { useCreateProject } from "@/services/queries";

const UPLOAD_TICK_MS = 300;
const FORM_ID = "novo-projeto";

const pillInput = "input-pill text-sm";

/**
 * "Upload de arquivos" step as a screen (design): the header and the footer
 * stay put, only the form scrolls. "Enviar para análise" stays disabled until
 * the required fields are filled and every file has finished uploading.
 */
export const NewProjectPage = () => {
  const navigate = useNavigate();
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [freeText, setFreeText] = useState("");
  const [items, setItems] = useState<UploadItem[]>([]);
  const [webSearch, setWebSearch] = useState(true);

  const summary = queueSummary(items);
  const nameMissing = name.trim() === "";
  const materialMissing = items.length === 0 && freeText.trim() === "";
  const ready = !nameMissing && !materialMissing && summary.uploading === 0 && !createProject.isPending;

  // MOCK upload: progress advances while any file is still "sending"
  useEffect(() => {
    if (summary.uploading === 0) return;
    const timer = setInterval(() => setItems(advance), UPLOAD_TICK_MS);
    return () => clearInterval(timer);
  }, [summary.uploading]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    createProject.mutate(
      { name, company, freeText, webSearch, files: items.map((item) => item.file) },
      { onSuccess: () => navigate(paths.projects()) },
    );
  };

  const hint =
    summary.uploading > 0
      ? `Aguarde o envio de ${pluralize(summary.uploading, "arquivo", "arquivos")} para continuar.`
      : nameMissing && materialMissing
        ? "Preencha o nome do projeto e anexe um documento ou escreva uma descrição."
        : nameMissing
          ? "Preencha o nome do projeto para continuar."
          : materialMissing
            ? "Anexe ao menos um documento ou escreva uma descrição do projeto."
            : "Tudo pronto para enviar.";

  const submitButton = (
    <button type="submit" form={FORM_ID} className="btn-primary" disabled={!ready}>
      {createProject.isPending ? "Enviando…" : "Enviar para análise"}
    </button>
  );

  return (
    <div className="flex flex-1 flex-col lg:min-h-0 lg:overflow-hidden">
      <PageHeader
        title="Novo projeto"
        description={<p>Envie o material do projeto.</p>}
        aside={submitButton}
      />

      <div className="flex w-full flex-1 flex-col p-4 lg:min-h-0">
        <form
          id={FORM_ID}
          onSubmit={handleSubmit}
          noValidate
          aria-labelledby="novo-projeto-titulo"
          className="flex flex-col overflow-hidden rounded-[28px] bg-white/80 shadow-[0_4px_16px_rgb(0_0_0/0.1)] lg:min-h-0 lg:flex-1"
        >
          <h2 id="novo-projeto-titulo" className="sr-only">
            Material do projeto
          </h2>
          <div className="scroll-visible flex flex-col gap-[18px] p-6 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pb-24">
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
                  aria-required
                  autoFocus
                />
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
              <textarea
                id="project-free-text"
                rows={1}
                className={`${pillInput} h-auto min-h-12 resize-none rounded-3xl py-3.5 field-sizing-content`}
                placeholder="Problema técnico, o que é novo, o que não se sabia se ia funcionar…"
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
              />
            </div>

            <section aria-labelledby="documents-title" className="flex flex-col gap-2">
              <div className="flex flex-wrap items-baseline gap-2">
                <h3 id="documents-title" className="text-base font-semibold">
                  Documentos do projeto
                </h3>
                {summary.count > 0 && (
                  <p className="text-xs text-fg-muted">
                    ({pluralize(summary.count, "arquivo", "arquivos")} · {formatFileSize(summary.bytes)})
                  </p>
                )}
              </div>
              <FileDropzone
                hasFiles={items.length > 0}
                onFiles={(files) => setItems((current) => addFiles(current, files))}
              />
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
              <span className="text-fg-muted">A versão fica gravada na análise e no documento de decisão.</span>
            </div>

            {createProject.isError && (
              <p role="alert" className="text-sm text-danger">
                Não foi possível enviar o projeto. Tente novamente.
              </p>
            )}
          </div>

          {/* Fixed footer; the form passes behind its fade */}
          <footer className="relative flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-track bg-white px-7 pt-4 pb-5">
            <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-full hidden h-20 bg-gradient-to-b from-white/0 to-white lg:block" />
            <p className="text-[13px] text-fg-muted" aria-live="polite">
              {hint}
            </p>
            <div className="flex gap-2.5">
              <Link to={paths.projects()} className="btn-secondary">
                Cancelar
              </Link>
              {submitButton}
            </div>
          </footer>
        </form>
      </div>
    </div>
  );
};
