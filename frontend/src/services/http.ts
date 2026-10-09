/*
 * Real API client (spec 14 E2/E3). Only services/ imports this.
 * Bearer token, one transparent refresh on 401 (never a loop), 10 s timeout.
 */

const TOKENS_KEY = "lei-do-bem:tokens";

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class AuthError extends Error {
  constructor(message = "E-mail ou sessão inválidos") {
    super(message);
    this.name = "AuthError";
  }
}

export const apiUrl = (): string =>
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export const loadTokens = (): TokenPair | null => {
  try {
    const raw = localStorage.getItem(TOKENS_KEY);
    return raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    return null;
  }
};

export const saveTokens = (tokens: TokenPair) =>
  localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));

export const clearTokens = () => localStorage.removeItem(TOKENS_KEY);

const request = async (path: string, init: RequestInit = {}): Promise<Response> => {
  const tokens = loadTokens();
  const headers = new Headers(init.headers);
  if (tokens?.accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${tokens.accessToken}`);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);
  try {
    return await fetch(`${apiUrl()}${path}`, { ...init, headers, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
};

/** One refresh attempt on 401; a second 401 gives up (no loop). */
const refreshTokens = async (): Promise<TokenPair | null> => {
  const tokens = loadTokens();
  if (!tokens?.refreshToken) return null;
  const response = await fetch(`${apiUrl()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: tokens.refreshToken }),
  });
  if (!response.ok) return null;
  const fresh = (await response.json()) as { access_token: string; refresh_token: string };
  const pair: TokenPair = { accessToken: fresh.access_token, refreshToken: fresh.refresh_token };
  saveTokens(pair);
  return pair;
};

export const apiFetch = async (path: string, init: RequestInit = {}): Promise<Response> => {
  const response = await request(path, init);
  if (response.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) return await request(path, init);
    clearTokens();
  }
  return response;
};

export const apiJson = async <T>(path: string, init: RequestInit = {}): Promise<T> => {
  const response = await apiFetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok) throw new ApiError(`API ${response.status} em ${path}`, response.status);
  return (await response.json()) as T;
};

/** POST/PUT with a JSON body. */
export const apiPost = <T>(path: string, body: unknown): Promise<T> =>
  apiJson<T>(path, { method: "POST", body: JSON.stringify(body) });

/** POST with multipart form-data (upload). */
export const apiPostForm = async <T>(path: string, form: FormData): Promise<T> => {
  const response = await apiFetch(path, { method: "POST", body: form });
  if (!response.ok) throw new ApiError(`API ${response.status} em ${path}`, response.status);
  return (await response.json()) as T;
};