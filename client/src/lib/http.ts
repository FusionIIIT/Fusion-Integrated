/** One axios instance for the whole app, with the interceptors the legacy
 *  academic SPA never had. */
import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,          // the session cookie, never a JS-readable token
  timeout: 15000,
});

/** Paired with the session cookie. Held in memory rather than a readable
 *  cookie, which the SPA could not read cross-origin in development. */
let csrfToken = "";
export function setCsrfToken(value: string) {
  csrfToken = value ?? "";
}

const UNSAFE = new Set(["post", "put", "patch", "delete"]);

http.interceptors.request.use((config) => {
  if (csrfToken && UNSAFE.has((config.method ?? "get").toLowerCase())) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

http.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) onUnauthorized?.();
    return Promise.reject(error);
  },
);

/** Pull a usable message out of the platform's error envelope. */
export function errorMessage(e: unknown): string {
  const env = (e as { response?: { data?: { error?: {
    message?: string; details?: { message?: string }[] } } } })
    ?.response?.data?.error;
  if (!env) return "Something went wrong. Please try again.";
  if (env.details?.length) {
    return env.details.map((d) => d.message).filter(Boolean).join(" ") ||
      env.message || "Request failed.";
  }
  return env.message ?? "Request failed.";
}

/** A `responseType: "blob"` request delivers the *error* body as a Blob too,
 *  which hides the envelope from errorMessage. Read it back before rethrowing. */
export async function readBlobError(e: unknown): Promise<unknown> {
  const res = (e as { response?: { data?: unknown } })?.response;
  if (res?.data instanceof Blob) {
    try {
      res.data = JSON.parse(await res.data.text());
    } catch {
      res.data = undefined;             // an HTML page, not our envelope
    }
  }
  return e;
}

export function errorStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } })?.response?.status;
}

export function requestId(e: unknown): string | undefined {
  return (e as { response?: { data?: { error?: { request_id?: string } } } })
    ?.response?.data?.error?.request_id;
}
