import { CloudUpload } from "lucide-react";
import { useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import type { FileRejection } from "react-dropzone";
import { MAX_FILE_BYTES } from "@/domain/documents";
import { formatFileSize } from "@/lib/format";

/*
 * ANY file type is accepted: the back-end identifies each file BY CONTENT
 * (pdf, csv, xlsx, md, json, txt, docx…) and flags unknown types for
 * validation instead of rejecting them — the front must not pre-bar them.
 * The known-formats list lives in domain/documents.ts (icon/kind); the
 * dropzone only enforces the size limit.
 */

interface FileDropzoneProps {
  onFiles: (files: File[]) => void;
  /** "Arraste mais arquivos…" once there are files */
  hasFiles: boolean;
}

/** Drop area for files and whole folders (react-dropzone walks dropped folders) */
export const FileDropzone = ({ onFiles, hasFiles }: FileDropzoneProps) => {
  const [rejections, setRejections] = useState<string[]>([]);
  const folderInput = useRef<HTMLInputElement>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxSize: MAX_FILE_BYTES,
    multiple: true,
    onDrop: (accepted, rejected: FileRejection[]) => {
      onFiles(accepted);
      setRejections(
        rejected.map(({ file, errors }) =>
          `${file.name}: ${errors[0]?.code === "file-too-large" ? "arquivo maior que o limite" : "não foi possível adicionar o arquivo"}`,
        ),
      );
    },
  });

  const onFolder = (files: FileList | null) => {
    const all = [...(files ?? [])];
    // A folder brings everything, any type: only the size limit applies
    onFiles(all.filter((f) => f.size <= MAX_FILE_BYTES));
    setRejections(
      all
        .filter((f) => f.size > MAX_FILE_BYTES)
        .map((f) => `${f.webkitRelativePath || f.name}: arquivo maior que o limite`),
    );
  };

  return (
    <div className="flex flex-col gap-2">
      <div
        {...getRootProps({
          className: `flex min-h-[139px] cursor-pointer flex-col items-center justify-center gap-2 rounded-[18px] border border-dashed border-action px-4 py-3.5 text-center transition-colors ${
            isDragActive ? "bg-accent-soft" : "bg-surface hover:bg-accent-soft/50"
          }`,
        })}
      >
        <input {...getInputProps()} aria-label="Selecionar arquivos" />
        <span className="flex size-12 items-center justify-center rounded-full bg-brand-blush text-accent">
          <CloudUpload className="size-6" aria-hidden />
        </span>
        <p className="text-base font-semibold">
          {isDragActive
            ? "Solte os arquivos ou pastas aqui"
            : hasFiles
              ? "Arraste mais arquivos ou clique para selecionar"
              : "Arraste arquivos ou clique para selecionar"}
        </p>
        <p className="text-xs text-fg-muted">
          Qualquer tipo de documento (PDF, DOCX, TXT, MD, CSV, XLSX, JSON e outros) · até{" "}
          {formatFileSize(MAX_FILE_BYTES)} por arquivo · pastas inteiras são aceitas{" "}
          <button
            type="button"
            className="btn-link"
            onClick={(e) => {
              e.stopPropagation();
              folderInput.current?.click();
            }}
          >
            (selecionar pasta)
          </button>
        </p>
      </div>
      <input
        ref={folderInput}
        type="file"
        multiple
        hidden
        aria-label="Selecionar uma pasta"
        {...{ webkitdirectory: "" }}
        onChange={(e) => {
          onFolder(e.target.files);
          e.target.value = "";
        }}
      />
      {rejections.length > 0 && (
        <ul role="alert" className="flex flex-col gap-0.5 text-xs text-danger">
          {rejections.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      )}
    </div>
  );
};