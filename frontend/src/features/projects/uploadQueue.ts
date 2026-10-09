import { recognizeDocumentKind } from "@/domain/documents";

/*
 * Files being added to a new project. MOCK: the upload is simulated on the
 * client (progress grows with time, faster for small files); nothing leaves
 * the browser until the back-end exists.
 */

export interface UploadItem {
  id: string;
  file: File;
  /** Relative path for files that came inside a dropped folder */
  name: string;
  kind: string;
  /** 0–1; 1 = "Pronto" */
  progress: number;
}

let counter = 0;

export const toUploadItem = (file: File): UploadItem => {
  const path = (file as File & { path?: string }).path?.replace(/^\.?\//, "");
  const name = path || file.name;
  return { id: `upload-${++counter}`, file, name, kind: recognizeDocumentKind(name), progress: 0 };
};

const sameFile = (a: File, b: File) =>
  a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;

/** Adds files that are not in the queue yet */
export const addFiles = (items: UploadItem[], files: File[]) => [
  ...items,
  ...files.filter((f) => !items.some((item) => sameFile(item.file, f))).map(toUploadItem),
];

/** One simulated tick (~300 ms): about 1 MB per tick, at least 8% */
export const advance = (items: UploadItem[]) =>
  items.map((item) =>
    item.progress >= 1
      ? item
      : { ...item, progress: Math.min(1, item.progress + Math.max(0.08, 1_000_000 / Math.max(1, item.file.size))) },
  );

export const queueSummary = (items: UploadItem[]) => ({
  count: items.length,
  bytes: items.reduce((sum, item) => sum + item.file.size, 0),
  uploading: items.filter((item) => item.progress < 1).length,
});

/** The first rows stay visible; the rest is folded into one "+ N arquivos" row */
export const VISIBLE_ROWS = 4;

export const foldRows = (items: UploadItem[]) => {
  const visible = items.slice(0, VISIBLE_ROWS);
  const rest = items.slice(VISIBLE_ROWS);
  if (rest.length <= 1) return { visible: items, rest: null };
  const kinds = [...new Set(rest.map((item) => item.kind.toLowerCase()))];
  return {
    visible,
    rest: {
      count: rest.length,
      kinds,
      bytes: rest.reduce((sum, item) => sum + item.file.size, 0),
      progress: rest.reduce((sum, item) => sum + item.progress, 0) / rest.length,
    },
  };
};
