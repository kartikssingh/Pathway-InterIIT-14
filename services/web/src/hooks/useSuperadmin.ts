/** Hooks for the superadmin monitoring views. */

import { useCallback, useEffect, useState } from "react";

import type { ApiState } from "./useApiState";

// ==================== SUPERADMIN MONITORING HOOKS ====================

/**
 * Hook to fetch superadmin dashboard
 */
export function useSuperadminDashboard(days: number = 7) {
  const [state, setState] = useState<ApiState<import("@/lib/api").SuperadminDashboard>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchDashboard = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getDashboard(days);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch superadmin dashboard');
      setState({ data: null, loading: false, error: err });
    }
  }, [days]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return {
    dashboard: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchDashboard,
  };
}

/**
 * Hook to fetch superadmin audit logs
 */
export function useSuperadminAuditLogs(params?: {
  admin_id?: number;
  action_type?: string;
  target_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").AuditLog[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchAuditLogs = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getMonitoringAuditLogs(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch audit logs');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  return {
    auditLogs: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchAuditLogs,
  };
}

/**
 * Hook to fetch metrics summary
 */
export function useMetricsSummary(days: number = 7) {
  const [state, setState] = useState<ApiState<import("@/lib/api").MetricsSummary>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchMetrics = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getMetricsSummary(days);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch metrics summary');
      setState({ data: null, loading: false, error: err });
    }
  }, [days]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return {
    metrics: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchMetrics,
  };
}

/**
 * Hook to fetch metrics history
 */
export function useMetricsHistory(params?: {
  metric_type?: string;
  metric_category?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").MetricHistory[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchHistory = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getMetricsHistory(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch metrics history');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    history: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchHistory,
  };
}

/**
 * Hook to fetch alert resolution statistics
 */
export function useAlertResolutions(days: number = 30) {
  const [state, setState] = useState<ApiState<import("@/lib/api").AlertResolutionStats>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchResolutions = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getAlertResolutions(days);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch alert resolutions');
      setState({ data: null, loading: false, error: err });
    }
  }, [days]);

  useEffect(() => {
    fetchResolutions();
  }, [fetchResolutions]);

  return {
    resolutions: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchResolutions,
  };
}

/**
 * Hook to fetch admin activity
 */
export function useAdminActivity(days: number = 30) {
  const [state, setState] = useState<ApiState<import("@/lib/api").AdminActivity[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchActivity = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getAdminActivity(days);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch admin activity');
      setState({ data: null, loading: false, error: err });
    }
  }, [days]);

  useEffect(() => {
    fetchActivity();
  }, [fetchActivity]);

  return {
    activity: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchActivity,
  };
}

/**
 * Hook to fetch health checks
 */
export function useHealthChecks(params?: {
  check_type?: string;
  component_name?: string;
  status?: string;
  severity?: string;
  is_resolved?: boolean;
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").HealthCheck[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchHealthChecks = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getHealthChecks(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch health checks');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchHealthChecks();
  }, [fetchHealthChecks]);

  return {
    healthChecks: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchHealthChecks,
  };
}

/**
 * Hook for health check actions
 */
export function useHealthCheckActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const updateHealthCheck = useCallback(async (
    healthId: number,
    data: import("@/lib/api").UpdateHealthCheckRequest
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const result = await superadminApi.updateHealthCheck(healthId, data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to update health check');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    updateHealthCheck,
    loading,
    error,
  };
}

/**
 * Hook to fetch system alerts
 */
export function useSystemAlerts(params?: {
  alert_type?: string;
  status?: string;
  severity?: string;
  component?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").SystemAlert[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchSystemAlerts = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getSystemAlerts(params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch system alerts');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchSystemAlerts();
  }, [fetchSystemAlerts]);

  return {
    systemAlerts: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchSystemAlerts,
  };
}

/**
 * Hook for system alert actions
 */
export function useSystemAlertActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const updateSystemAlert = useCallback(async (
    alertId: number,
    data: import("@/lib/api").UpdateSystemAlertRequest
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const result = await superadminApi.updateSystemAlert(alertId, data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to update system alert');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    updateSystemAlert,
    loading,
    error,
  };
}

/**
 * Hook to fetch system status
 */
export function useSystemStatus() {
  const [state, setState] = useState<ApiState<import("@/lib/api").SystemStatus>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchStatus = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { superadminApi } = await import("@/lib/api");
      const data = await superadminApi.getSystemStatus();
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch system status');
      setState({ data: null, loading: false, error: err });
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return {
    status: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchStatus,
  };
}
