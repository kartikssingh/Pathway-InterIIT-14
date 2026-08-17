"use client";

import { useMemo } from "react";

import { ServerDown } from "@/components/ServerDown";
import { useHealthCheck } from "@/hooks/useHealthCheck";

/**
 * Blocks the console behind a "server unavailable" screen when the API stops
 * answering.
 *
 * The config object is memoised: passing a fresh literal on every render made
 * the hook's effect re-run each time, tearing down and recreating the polling
 * interval. The `endpoint` option is gone — the hook now always probes
 * `/health/live`, which reports unhealthy when the database is down instead of
 * merely confirming that something is listening on the port.
 */
export function HealthCheckWrapper({ children }: { children: React.ReactNode }) {
  const config = useMemo(
    () => ({
      checkInterval: 10_000,
      failureThreshold: 2, // ~20 seconds before the screen appears
      timeout: 3_000,
    }),
    [],
  );

  const { isHealthy, consecutiveFailures, lastCheckTime, error, checkNow } =
    useHealthCheck(config);

  if (!isHealthy) {
    return (
      <ServerDown
        onRetry={checkNow}
        consecutiveFailures={consecutiveFailures}
        lastCheckTime={lastCheckTime}
        error={error}
      />
    );
  }

  return <>{children}</>;
}
