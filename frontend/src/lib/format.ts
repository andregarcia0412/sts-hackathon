const dateFormatter = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

export const formatDate = (iso: string) => dateFormatter.format(new Date(iso));

export const formatDateTime = (iso: string) =>
  dateTimeFormatter.format(new Date(iso));

export const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
};

export const pluralize = (count: number, singular: string, plural: string) =>
  `${count} ${count === 1 ? singular : plural}`;
