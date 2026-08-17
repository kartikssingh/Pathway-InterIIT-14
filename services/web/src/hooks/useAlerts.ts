/** Hooks for compliance alerts: listing, live feed, trends and actions. */

import { useCallback, useEffect, useState } from "react";

import { alertApi } from "@/lib/api";

import type { ApiState } from "./useApiState";

// ==================== ALERT HOOKS ====================

/**
 * Hook to fetch critical alerts
 */
export function useCriticalAlerts(params?: {
  limit?: number;
  severity?: string;
  hours?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").CriticalAlert[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { alertApi } = await import("@/lib/api");
      const data = await alertApi.getCriticalAlerts(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch critical alerts');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return {
    alerts: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchAlerts,
  };
}

/**
 * Hook to fetch live alerts with polling support
 */
export function useLiveAlerts(params?: {
  limit?: number;
  since?: string;
}, pollInterval?: number) {
  const [state, setState] = useState<ApiState<import("@/lib/api").LiveAlert[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { alertApi } = await import("@/lib/api");
      const data = await alertApi.getLiveAlerts(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch live alerts');
      
      // In development, provide helpful hints
      if (process.env.NODE_ENV === 'development') {
        console.warn(
          '[useLiveAlerts] Failed to fetch alerts. '
          + 'If backend is not running, check DASHBOARD_BACKEND_REQUIREMENTS.md for setup instructions.'
        );
      }
      
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchAlerts();
    
    if (pollInterval && pollInterval > 0) {
      const interval = setInterval(fetchAlerts, pollInterval);
      return () => clearInterval(interval);
    }
  }, [fetchAlerts, pollInterval]);

  return {
    alerts: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchAlerts,
  };
}

/**
 * Hook to fetch alert trend data
 */
export function useAlertTrend(params?: {
  period?: string;
  interval?: string;
  severity?: string;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").AlertTrendResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchTrend = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { alertApi } = await import("@/lib/api");
      const data = await alertApi.getAlertTrend(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch alert trend');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchTrend();
  }, [fetchTrend]);

  return {
    trend: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchTrend,
  };
}

/**
 * Hook to fetch compliance alerts with filtering
 */
export function useComplianceAlerts(params?: {
  limit?: number;
  severity?: string;
  status?: string;
  skip?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").ComplianceAlertListResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { alertApi } = await import("@/lib/api");
      const data = await alertApi.getComplianceAlerts(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch compliance alerts');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return {
    alerts: state.data?.items || null,
    total: state.data?.total || 0,
    loading: state.loading,
    error: state.error,
    refetch: fetchAlerts,
  };
}

/**
 * Hook to fetch unclassified alerts (alerts pending review)
 * Uses GET /dashboard/alerts/unclassified endpoint
 * Returns active/investigating alerts
 * 
 * Classification logic:
 * - status = 'resolved' → Equivalent to true positive
 * - status = 'dismissed' → Equivalent to false positive
 * - status = 'active' or 'investigating' → Pending review
 */
export function useUnclassifiedAlerts(params?: {
  limit?: number;
  skip?: number;
  severity?: string;
  status?: string;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").UnclassifiedAlertsResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { alertApi } = await import("@/lib/api");
      const data = await alertApi.getUnclassifiedAlerts(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch unclassified alerts');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return {
    alerts: state.data?.alerts || null,
    total: state.data?.total || 0,
    loading: state.loading,
    error: state.error,
    refetch: fetchAlerts,
  };
}

/**
 * Hook for alert actions (dismiss, resolve, acknowledge, update)
 */
export function useAlertActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const dismissAlert = useCallback(async (alertId: string, request?: import("@/lib/api").AlertDismissRequest) => {
    setLoading(true);
    setError(null);
    
    try {
      const { alertApi } = await import("@/lib/api");
      const result = await alertApi.dismissAlert(alertId, request);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to dismiss alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const updateComplianceAlert = useCallback(async (alertId: number, update: import("@/lib/api").ComplianceAlertUpdate) => {
    setLoading(true);
    setError(null);
    
    try {
      const { alertApi } = await import("@/lib/api");
      const result = await alertApi.updateComplianceAlert(alertId, update);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to update alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const acknowledgeComplianceAlert = useCallback(async (alertId: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const { alertApi } = await import("@/lib/api");
      const result = await alertApi.acknowledgeComplianceAlert(alertId);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to acknowledge alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const resolveComplianceAlert = useCallback(async (alertId: number, notes?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const { alertApi } = await import("@/lib/api");
      const result = await alertApi.resolveComplianceAlert(alertId, notes);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to resolve alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const dismissComplianceAlert = useCallback(async (alertId: number, reason?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const { alertApi } = await import("@/lib/api");
      const result = await alertApi.dismissComplianceAlert(alertId, reason);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to dismiss alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  // ❌ REMOVED: Alert classification is no longer supported in backend
  // const markAlert = useCallback(async (alertId: number, isPositive: boolean, notes?: string) => {
  //   setLoading(true);
  //   setError(null);
  //   
  //   try {
  //     const { alertApi } = await import("@/lib/api");
  //     const result = await alertApi.markAlert(alertId, {
  //       is_true_positive: isPositive,
  //       notes,
  //     });
  //     setLoading(false);
  //     return result;
  //   } catch (err) {
  //     const error = err instanceof Error ? err : new Error('Failed to mark alert');
  //     setError(error);
  //     setLoading(false);
  //     throw error;
  //   }
  // }, []);

  return {
    dismissAlert,
    updateComplianceAlert,
    acknowledgeComplianceAlert,
    resolveComplianceAlert,
    dismissComplianceAlert,
    loading,
    error,
  };
}
