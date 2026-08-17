/**
 * The shared request-state primitive every data hook builds on.
 *
 * Split out of the former 1,500-line `useApi.ts`, with three fixes:
 *
 *   - a failed request wiped `data` back to `null`, so a transient error blanked
 *     a table that was already showing perfectly good rows; the previous data is
 *     kept and `error` is set alongside it;
 *   - `console.error` ran on every failure in production;
 *   - state was set after the component unmounted when a request finished late.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

export interface UseApiStateOptions {
  autoFetch?: boolean;
  onError?: (error: Error) => void;
}

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/** Human-readable text for any thrown value. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.userMessage;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

/** True when retrying without user input could plausibly succeed. */
export function isRetryable(error: unknown): boolean {
  return error instanceof ApiError ? error.isRetryable : false;
}

export function useApiState<T>(
  initialData: T | null = null,
): [ApiState<T>, (asyncFn: () => Promise<T>) => Promise<void>, () => void] {
  const [state, setState] = useState<ApiState<T>>({
    data: initialData,
    loading: false,
    error: null,
  });

  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const execute = useCallback(async (asyncFn: () => Promise<T>) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const result = await asyncFn();
      if (mounted.current) setState({ data: result, loading: false, error: null });
    } catch (caught) {
      // A caller-cancelled request is not a failure worth showing.
      if (caught instanceof DOMException && caught.name === "AbortError") return;

      const error = caught instanceof Error ? caught : new Error(describeError(caught));
      if (process.env.NODE_ENV !== "production") {
        console.error("[useApiState]", error);
      }
      // Keep whatever was on screen; surface the error next to it.
      if (mounted.current) setState((prev) => ({ ...prev, loading: false, error }));
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: initialData, loading: false, error: null });
  }, [initialData]);

  return [state, execute, reset];
}
