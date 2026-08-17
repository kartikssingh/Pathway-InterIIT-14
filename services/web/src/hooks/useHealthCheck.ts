/**
 * Polls the API so the console can show a "server unavailable" screen.
 *
 * Fixes:
 *   - it probed `/` and accepted 404 and 405 as healthy, so any process
 *     listening on the port counted as a working backend — including one whose
 *     database was down. It now calls `/health/live`, which the API answers only
 *     when it is actually able to serve;
 *   - `mergedConfig` was rebuilt on every render, so `performHealthCheck` was a
 *     new function every render and the effect tore down and recreated the
 *     interval each time;
 *   - the abort timer leaked whenever `fetch` rejected before `clearTimeout`;
 *   - polling continued while the tab was hidden; it now pauses and re-checks
 *     immediately on return.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { checkApiHealth } from "@/lib/api";

export interface HealthCheckConfig {
  /** Milliseconds between checks while the tab is visible. */
  checkInterval?: number;
  /** Consecutive failures before the server is reported as down. */
  failureThreshold?: number;
  /** Per-request timeout in milliseconds. */
  timeout?: number;
}

export interface HealthCheckState {
  isHealthy: boolean;
  isChecking: boolean;
  consecutiveFailures: number;
  lastCheckTime: Date | null;
  error: Error | null;
}

const DEFAULT_CONFIG: Required<HealthCheckConfig> = {
  checkInterval: 30_000,
  failureThreshold: 3,
  timeout: 5_000,
};

export function useHealthCheck(config: HealthCheckConfig = {}) {
  const { checkInterval, failureThreshold, timeout } = useMemo(
    () => ({ ...DEFAULT_CONFIG, ...config }),
    [config.checkInterval, config.failureThreshold, config.timeout],
  );

  const [state, setState] = useState<HealthCheckState>({
    // Optimistic: assume healthy until a check has actually failed, so the app
    // does not flash the error screen on first paint.
    isHealthy: true,
    isChecking: true,
    consecutiveFailures: 0,
    lastCheckTime: null,
    error: null,
  });

  const failures = useRef(0);
  const mounted = useRef(true);

  const check = useCallback(async () => {
    if (!mounted.current) return;
    setState((prev) => ({ ...prev, isChecking: true }));

    const healthy = await checkApiHealth(timeout);
    if (!mounted.current) return;

    if (healthy) {
      failures.current = 0;
      setState({
        isHealthy: true,
        isChecking: false,
        consecutiveFailures: 0,
        lastCheckTime: new Date(),
        error: null,
      });
      return;
    }

    failures.current += 1;
    const down = failures.current >= failureThreshold;
    setState({
      isHealthy: !down,
      isChecking: false,
      consecutiveFailures: failures.current,
      lastCheckTime: new Date(),
      error: new Error(`Health check failed (${failures.current}/${failureThreshold})`),
    });
  }, [failureThreshold, timeout]);

  useEffect(() => {
    mounted.current = true;
    void check();

    const interval = setInterval(() => {
      // No point polling a backend nobody is looking at.
      if (document.visibilityState === "visible") void check();
    }, checkInterval);

    const onVisible = () => {
      if (document.visibilityState === "visible") void check();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      mounted.current = false;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [check, checkInterval]);

  return {
    ...state,
    checkNow: check,
    config: { checkInterval, failureThreshold, timeout },
  };
}
