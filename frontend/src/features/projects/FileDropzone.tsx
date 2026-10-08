import { FileText, Upload, X } from "lucide-react";
import { useDropzone } from "react-dropzone";
import type { FileRejection } from "react-dropzone";
import { useState } from "react";
import { formatFileSize } from "@/lib/format";

const ACCEPTED_FILES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
  "text/plain": [".txt"],
};

const MAX_FILE_SIZE = 20 * 1024 * 1024;

const sameFile = (a: File, b: File) =>
  a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;

interface FileDropzoneProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export const FileDropzone = ({ files, onChange }: FileDropzoneProps) => {
  const [rejections, setRejections] = useState<FileRejection[]>([]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED_FILES,
    maxSize: MAX_FILE_SIZE,
    multiple: true,
    onDrop: (accepted, rejected) => {
      const added = accepted.filter((f) => !files.some((e) => sameFile(e, f)));
      onChange([...files, ...added]);
      setRejections(rejected);
    },
  });

  return (
    <div className="space-y-2">
      <div
        {...getRootProps({
          className: `flex cursor-pointer flex-col items-center gap-1 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors ${
            isDragActive
              ? "border-accent bg-accent-soft"
              : "border-border-strong hover:bg-surface-muted"
          }`,
        })}
      >
        <input {...getInputProps()} aria-label="Selecionar arquivos" />
        <Upload className="size-6 text-fg-muted" aria-hidden />
        <p className="text-sm font-medium">
          {isDragActive
            ? "Solte os arquivos aqui"
            : "Arraste arquivos ou clique para selecionar"}
        </p>
        <p className="text-xs text-fg-muted">
          PDF, DOCX ou TXT · até {formatFileSize(MAX_FILE_SIZE)} por arquivo
        </p>
      </div>

      {rejections.length > 0 && (
        <ul role="alert" className="space-y-0.5 text-xs text-danger">
          {rejections.map(({ file, errors }) => (
            <li key={file.name}>
              {file.name}:{" "}
              {errors[0]?.code === "file-too-large"
                ? "arquivo maior que o limite"
                : "formato não aceito"}
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <ul className="divide-y divide-border rounded-md border border-border">
          {files.map((file) => (
            <li
              key={`${file.name}-${file.size}-${file.lastModified}`}
              className="flex items-center gap-2 px-3 py-2 text-sm"
            >
              <FileText className="size-4 shrink-0 text-fg-muted" aria-hidden />
              <span className="min-w-0 flex-1 truncate">{file.name}</span>
              <span className="text-xs text-fg-muted tabular-nums">
                {formatFileSize(file.size)}
              </span>
              <button
                type="button"
                className="btn-ghost p-1"
                aria-label={`Remover ${file.name}`}
                onClick={() => onChange(files.filter((f) => f !== file))}
              >
                <X className="size-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
