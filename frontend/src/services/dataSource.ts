/*
 * Data source selection (spec 14 E1): "mock" (fictitious, default),
 * "static" (JSONs exported by backend-export-frontend) or "api" (the real
 * back-end — E2/E3). Only services/ reads this; screens never do.
 */

export type DataSource = "mock" | "static" | "api";

const raw = (): string => import.meta.env.VITE_DATA_SOURCE ?? "";

export const dataSource = (): DataSource => {
  const value = raw().trim().toLowerCase();
  return value === "static" || value === "api" ? value : "mock";
};

export const staticApiDir = (): string =>
  (import.meta.env.VITE_STATIC_API_DIR as string | undefined)?.trim() || "./static-api";

export const dataSourceLabel = (): string => {
  const source = dataSource();
  if (source === "static") return "Dados estáticos extraídos do banco (modo estático)";
  if (source === "api") return "Dados do pipeline (API)";
  return "EXEMPLO FICTÍCIO";
};