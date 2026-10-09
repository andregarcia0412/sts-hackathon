import { CloudUpload } from "lucide-react";
import { useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import type { FileRejection } from "react-dropzone";
import { MAX_FILE_BYTES, isAcceptedFile } from "@/domain/documents";
import { ACCEPTED_FILE_TYPES } from "@/features/projects/acceptedFiles";
import { formatFileSize } from "@/lib/format";

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
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_BYTES,
    multiple: true,
    onDrop: (accepted, rejected: FileRejection[]) => {
      onFiles(accepted);
      setRejections(
        rejected.map(({ file, errors }) =>
          `${file.name}: ${errors[0]?.code === "file-too-large" ? "arquivo maior que o limite" : "formato não aceito"}`,
        ),
      );
    },
  });

  const onFolder = (files: FileList | null) => {
    const all = [...(files ?? [])];
    // A folder brings everything: keep the accepted formats, report the others
    onFiles(all.filter((f) => isAcceptedFile(f.name) && f.size <= MAX_FILE_BYTES));
    setRejections(
      all
        .filter((f) => !isAcceptedFile(f.name) || f.size > MAX_FILE_BYTES)
        .map((f) => `${f.webkitRelativePath || f.name}: ${f.size > MAX_FILE_BYTES ? "arquivo maior que o limite" : "formato não aceito"}`),
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
          PDF, DOCX, TXT, MD, CSV, XLSX ou JSON · até {formatFileSize(MAX_FILE_BYTES)} por arquivo ·
          pastas inteiras são aceitas{" "}
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
