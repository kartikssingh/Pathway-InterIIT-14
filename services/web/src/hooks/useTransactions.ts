/** Hooks for the transaction ledger. */

import { useCallback, useEffect, useState } from "react";

import { transactionApi, type Transaction as ApiTransaction } from "@/lib/api";

import type { ApiState } from "./useApiState";

// ==================== TRANSACTION HOOKS ====================

/**
 * Hook to fetch individual transactions (updated for new backend schema)
 * Returns individual transaction records, not aggregations
 */
export function useTransactions(params?: { 
  skip?: number; 
  limit?: number;
  user_id?: number; // Optional filter by user
}) {
  const [state, setState] = useState<ApiState<ApiTransaction[]>>({
    data: null,
    loading: true,
    error: null,
  });

  // Stringify params for stable dependency tracking
  const paramsKey = JSON.stringify(params || {});

  const fetchTransactions = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Fetch individual transactions from new API
      const response = await transactionApi.getTransactions({ 
        skip: params?.skip, 
        limit: params?.limit || 100 
      });
      
      // Extract items from response
      const transactions = response.items || [];
      
      setState({ data: transactions, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch transactions');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  return {
    transactions: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchTransactions,
  };
}

/**
 * Hook to fetch transactions for a specific user
 * Returns individual transaction records for the user
 */
export function useUserTransactionStats(userId: number | null) {
  const [state, setState] = useState<ApiState<ApiTransaction[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchTransactionStats = useCallback(async () => {
    if (!userId) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await transactionApi.getUserTransactions(userId, { limit: 100 });
      const transactions = response.items || [];
      setState({ data: transactions, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch user transactions');
      setState({ data: null, loading: false, error: err });
    }
  }, [userId]);

  useEffect(() => {
    fetchTransactionStats();
  }, [fetchTransactionStats]);

  return {
    transactionStats: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchTransactionStats,
  };
}

/**
 * @deprecated Use useUserTransactionStats instead
 * Maintained for backward compatibility
 */
export function useTransaction(transactionId: number | null) {
  console.warn('useTransaction is deprecated. Use useUserTransactionStats with user_id instead.');
  return useUserTransactionStats(transactionId);
}

/**
 * Hook for transaction actions
 * Note: Transaction creation endpoint may not be available in the new schema
 * Transactions are typically created by the backend transaction processing system
 */
export function useTransactionActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // ❌ Transaction creation is typically handled by the backend, not frontend
  // This is kept for backward compatibility but may not work with new schema
  const createTransaction = useCallback(async (data: Partial<ApiTransaction>) => {
    console.warn('Transaction creation endpoint may not be available. Transactions are typically created by backend systems.');
    setLoading(true);
    setError(null);
    
    try {
      // Note: This endpoint likely doesn't exist in the new backend
      throw new Error('Transaction creation not supported in new schema');
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create transaction');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    createTransaction,
    loading,
    error,
  };
}
