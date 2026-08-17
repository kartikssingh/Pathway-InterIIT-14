/**
 * The HTTP client every API module shares.
 *
 * Replaces the `apiRequest` helper that used to sit in the middle of
 * `lib/api.ts`. That version:
 *
 *   - `console.log`ed the full response body of every request, so customer PII
 *     landed in the browser console in production;
 *   - had no timeout, so a hung backend left a spinner on screen forever;
 *   - had no abort support, so navigating away kept the request alive and the
 *     late response tried to set state on an unmounted component;
 *   - only understood FastAPI's old `{detail: ...}` error shape and produced
 *     `"[object Object]"` for validation errors, which return an array;
 *   - reached for `localStorage` on every call with no reaction to a 401, so an
 *     expired token produced an endlessly failing page rather than a redirect.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8001";

/** Requests that take longer than this are aborted. */
const DEFAULT_TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? 20_000);

/** Idempotent requests are retried this many times on a network/5xx failure. */
const MAX_RETRIES = 2;

const TOKEN_KEY = "access_token";
const ROLE_KEY = "user_role";
const USERNAME_KEY = "username";

const isBrowser = typeof window !== "undefined";
const isDev = process.env.NODE_ENV !== "production";

/* -------------------------------------------------------------------------- */
/* Errors                                                                     */
/* -------------------------------------------------------------------------- */

export interface FieldError {
  field: string;
  message: string;
  type?: string;
}

/** A failed request, with everything a caller might branch on. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly endpoint: string;
  readonly requestId?: string;
  readonly fields: FieldError[];

  constructor(init: {
    message: string;
    status: number;
    code?: string;
    endpoint: string;
    requestId?: string;
    fields?: FieldError[];
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code ?? "unknown_error";
    this.endpoint = init.endpoint;
    this.requestId = init.requestId;
    this.fields = init.fields ?? [];
  }

  /** No response at all — the backend is unreachable. */
  get isNetworkError(): boolean {
    return this.status === 0;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isValidationError(): boolean {
    return this.status === 422;
  }

  /** Worth trying again without the user changing anything. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }

  /** Wording suitable for showing to an operator. */
  get userMessage(): string {
    if (this.isNetworkError) {
      return `Cannot reach the API at ${API_BASE_URL}. Check that the backend is running.`;
    }
    if (this.isUnauthorized) return "Your session has expired. Please sign in again.";
    if (this.isForbidden) return "You do not have permission to do that.";
    if (this.isValidationError && this.fields.length) {
      return this.fields.map((f) => `${f.field}: ${f.message}`).join("; ");
    }
    if (this.status >= 500) return "The server ran into a problem. Please try again.";
    return this.message;
  }
}

/* -------------------------------------------------------------------------- */
/* Session                                                                    */
/* -------------------------------------------------------------------------- */

export function getToken(): string | null {
  return isBrowser ? localStorage.getItem(TOKEN_KEY) : null;
}

export function storeSession(token: string, role: string, username: string): void {
  if (!isBrowser) return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
  localStorage.setItem(USERNAME_KEY, username);
}

export function clearSession(): void {
  if (!isBrowser) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

/**
 * Called once when a request comes back 401.
 *
 * The session is cleared and the app is sent to the login page — previously an
 * expired token just produced a page full of failed panels.
 */
let handlingUnauthorized = false;
function onUnauthorized(): void {
  if (!isBrowser || handlingUnauthorized) return;
  handlingUnauthorized = true;
  clearSession();
  if (!window.location.pathname.startsWith("/login") && window.location.pathname !== "/") {
    window.location.href = "/";
  }
  window.setTimeout(() => {
    handlingUnauthorized = false;
  }, 1000);
}

/* -------------------------------------------------------------------------- */
/* Query strings                                                              */
/* -------------------------------------------------------------------------- */

export type QueryValue = string | number | boolean | null | undefined;

/**
 * Build a query string, dropping empty values.
 *
 * The same twelve-line `URLSearchParams` block was pasted into ~30 functions;
 * several of them forgot the `value !== undefined` guard and sent the literal
 * string `"undefined"` to the API.
 */
export function buildQuery(params?: Record<string, QueryValue>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.append(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

/* -------------------------------------------------------------------------- */
/* Request                                                                    */
/* -------------------------------------------------------------------------- */

interface ErrorEnvelope {
  error?: { code?: string; message?: string; details?: { fields?: FieldError[] } };
  request_id?: string;
  detail?: unknown; // the API's older shape, still emitted by some handlers
}

function parseError(
  status: number,
  endpoint: string,
  body: ErrorEnvelope | null,
  requestId?: string,
): ApiError {
  // Current shape: { error: { code, message, details }, request_id }
  if (body?.error?.message) {
    return new ApiError({
      message: body.error.message,
      status,
      code: body.error.code,
      endpoint,
      requestId: body.request_id ?? requestId,
      fields: body.error.details?.fields ?? [],
    });
  }

  // Legacy FastAPI shapes: a string, or an array of validation errors.
  const detail = body?.detail;
  if (typeof detail === "string") {
    return new ApiError({ message: detail, status, endpoint, requestId });
  }
  if (Array.isArray(detail)) {
    const fields: FieldError[] = detail.map((item) => {
      const entry = item as { loc?: unknown[]; msg?: string; type?: string };
      return {
        field: (entry.loc ?? []).slice(1).join(".") || "body",
        message: entry.msg ?? "invalid",
        type: entry.type,
      };
    });
    return new ApiError({
      message: fields.map((f) => `${f.field}: ${f.message}`).join("; "),
      status,
      code: "validation_failed",
      endpoint,
      requestId,
      fields,
    });
  }

  return new ApiError({ message: `Request failed with status ${status}`, status, endpoint, requestId });
}

export interface RequestOptions extends Omit<RequestInit, "signal"> {
  /** Abort signal from the caller; combined with the internal timeout. */
  signal?: AbortSignal;
  /** Override the default timeout for this request. */
  timeoutMs?: number;
  /** Skip the Authorization header (used by login). */
  anonymous?: boolean;
  /** Retry count for this call; defaults to `MAX_RETRIES` for GET, 0 otherwise. */
  retries?: number;
}

function combineSignals(external: AbortSignal | undefined, timeoutMs: number) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException("Timeout", "TimeoutError")), timeoutMs);
  external?.addEventListener("abort", () => controller.abort(external.reason), { once: true });
  return { signal: controller.signal, cancel: () => clearTimeout(timer) };
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, anonymous, retries, signal, ...init } = options;
  const method = (init.method ?? "GET").toUpperCase();
  const attempts = (retries ?? (method === "GET" ? MAX_RETRIES : 0)) + 1;
  const url = `${API_BASE_URL}${endpoint}`;

  let lastError: ApiError | null = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const token = anonymous ? null : getToken();
    const { signal: requestSignal, cancel } = combineSignals(signal, timeoutMs);

    try {
      const response = await fetch(url, {
        ...init,
        signal: requestSignal,
        headers: {
          Accept: "application/json",
          ...(init.body && !(init.body instanceof FormData)
            ? { "Content-Type": "application/json" }
            : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...init.headers,
        },
      });

      const requestId = response.headers.get("X-Request-ID") ?? undefined;

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as ErrorEnvelope | null;
        const error = parseError(response.status, endpoint, body, requestId);

        if (error.isUnauthorized && !anonymous) onUnauthorized();
        if (error.isRetryable && attempt < attempts) {
          lastError = error;
          await sleep(200 * 2 ** (attempt - 1));
          continue;
        }
        // 404s are expected while an endpoint is still being built; do not
        // present them as failures in the console.
        if (isDev && !error.isNotFound) {
          console.error(`[api] ${method} ${endpoint} -> ${error.status}`, error.message);
        }
        throw error;
      }

      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    } catch (caught) {
      if (caught instanceof ApiError) throw caught;

      const aborted = caught instanceof DOMException && caught.name === "AbortError";
      const timedOut = caught instanceof DOMException && caught.name === "TimeoutError";

      // A caller-initiated abort is not an error worth reporting.
      if (aborted && signal?.aborted) throw caught;

      const error = new ApiError({
        message: timedOut
          ? `Request to ${endpoint} timed out after ${timeoutMs} ms`
          : `Cannot reach the API at ${API_BASE_URL}`,
        status: 0,
        code: timedOut ? "timeout" : "network_error",
        endpoint,
      });

      if (attempt < attempts) {
        lastError = error;
        await sleep(200 * 2 ** (attempt - 1));
        continue;
      }
      throw error;
    } finally {
      cancel();
    }
  }

  throw lastError ?? new ApiError({ message: "Request failed", status: 0, endpoint });
}

/** `multipart/form-data` upload — the browser must set the boundary itself. */
export async function requestMultipart<T>(
  endpoint: string,
  formData: FormData,
  options: Omit<RequestOptions, "body" | "headers"> = {},
): Promise<T> {
  return apiRequest<T>(endpoint, {
    ...options,
    method: options.method ?? "POST",
    body: formData,
    // Uploads are large; give them longer than a normal request.
    timeoutMs: options.timeoutMs ?? 120_000,
    retries: 0,
  });
}

/** Liveness probe used by the health banner. */
export async function checkApiHealth(timeoutMs = 4_000): Promise<boolean> {
  try {
    await apiRequest("/health/live", { anonymous: true, timeoutMs, retries: 0 });
    return true;
  } catch {
    return false;
  }
}
