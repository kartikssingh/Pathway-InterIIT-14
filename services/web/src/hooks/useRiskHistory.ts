/** Hooks for a user's risk-score history and sanctions screening records. */

import { useCallback, useEffect, useState } from "react";

import { toxicityHistoryApi, userSanctionMatchApi } from "@/lib/api";

import type { ApiState } from "./useApiState";

// ==================== TOXICITY HISTORY HOOKS ====================

/**
 * Hook to fetch toxicity history for a user
 */
export function useToxicityHistory(userId: number | null, params?: {
  skip?: number;
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").ToxicityHistory[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchToxicityHistory = useCallback(async () => {
    if (!userId) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { toxicityHistoryApi } = await import("@/lib/api");
      const data = await toxicityHistoryApi.getToxicityHistory(userId, params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch toxicity history');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, paramsKey]);

  useEffect(() => {
    fetchToxicityHistory();
  }, [fetchToxicityHistory]);

  return {
    toxicityHistory: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchToxicityHistory,
  };
}

/**
 * Hook for toxicity history actions (create)
 */
export function useToxicityHistoryActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createToxicityHistory = useCallback(async (
    userId: number, 
    data: import("@/lib/api").CreateToxicityHistoryRequest
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const { toxicityHistoryApi } = await import("@/lib/api");
      const result = await toxicityHistoryApi.createToxicityHistory(userId, data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create toxicity history');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    createToxicityHistory,
    loading,
    error,
  };
}

// ==================== USER SANCTION MATCHES HOOKS ====================

/**
 * Hook to fetch sanction matches for a user
 */
export function useUserSanctionMatches(userId: number | null, params?: {
  skip?: number;
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<import("@/lib/api").UserSanctionMatch[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const paramsKey = JSON.stringify(params || {});

  const fetchSanctionMatches = useCallback(async () => {
    if (!userId) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const { userSanctionMatchApi } = await import("@/lib/api");
      const data = await userSanctionMatchApi.getSanctionMatches(userId, params);
      setState({ data, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch sanction matches');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, paramsKey]);

  useEffect(() => {
    fetchSanctionMatches();
  }, [fetchSanctionMatches]);

  return {
    sanctionMatches: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchSanctionMatches,
  };
}

/**
 * Hook for sanction match actions (create)
 */
export function useUserSanctionMatchActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createSanctionMatch = useCallback(async (
    userId: number, 
    data: import("@/lib/api").CreateUserSanctionMatchRequest
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const { userSanctionMatchApi } = await import("@/lib/api");
      const result = await userSanctionMatchApi.createSanctionMatch(userId, data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create sanction match');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    createSanctionMatch,
    loading,
    error,
  };
}
