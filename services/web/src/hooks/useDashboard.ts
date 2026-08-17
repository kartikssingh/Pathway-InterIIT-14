/** Hooks for the operator dashboard aggregates. */

import { useCallback, useEffect, useState } from "react";

import {
  dashboardApi,
  type DashboardSummary,
  type FlaggedTransaction,
  type RiskDistribution,
} from "@/lib/api";

import type { ApiState } from "./useApiState";

// ==================== DASHBOARD HOOKS ====================

/**
 * Hook to fetch dashboard summary data
 */
export function useDashboard() {
  const [state, setState] = useState<ApiState<{
    summary: DashboardSummary;
    riskDistribution: RiskDistribution;
    flaggedTransactions: FlaggedTransaction[];
  }>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchDashboard = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const [summary, riskDistribution, flaggedTransactions] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getRiskDistribution(),
        dashboardApi.getFlaggedTransactions(10),
      ]);
      
      setState({
        data: { summary, riskDistribution, flaggedTransactions },
        loading: false,
        error: null,
      });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch dashboard data');
      setState({ data: null, loading: false, error: err });
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return {
    summary: state.data?.summary || null,
    riskDistribution: state.data?.riskDistribution || null,
    flaggedTransactions: state.data?.flaggedTransactions || null,
    loading: state.loading,
    error: state.error,
    refetch: fetchDashboard,
  };
}

/**
 * Hook to fetch risk distribution
 */
export function useRiskDistribution() {
  const [state, setState] = useState<ApiState<RiskDistribution>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchRiskDistribution = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await dashboardApi.getRiskDistribution();
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch risk distribution');
      setState({ data: null, loading: false, error: err });
    }
  }, []);

  useEffect(() => {
    fetchRiskDistribution();
  }, [fetchRiskDistribution]);

  return {
    riskDistribution: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchRiskDistribution,
  };
}

/**
 * Hook to fetch flagged transactions
 */
export function useFlaggedTransactions(limit: number = 10) {
  const [state, setState] = useState<ApiState<FlaggedTransaction[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchFlaggedTransactions = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await dashboardApi.getFlaggedTransactions(limit);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch flagged transactions');
      setState({ data: null, loading: false, error: err });
    }
  }, [limit]);

  useEffect(() => {
    fetchFlaggedTransactions();
  }, [fetchFlaggedTransactions]);

  return {
    flaggedTransactions: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchFlaggedTransactions,
  };
}
