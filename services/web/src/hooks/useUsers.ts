/** Hooks for user records and the actions an operator can take on them. */

import { useCallback, useEffect, useState } from "react";

import { transactionApi, userApi, type User as ApiUser } from "@/lib/api";
import {
  generateUserEventsFromTransactions,
  transformApiUserToComponent,
  type ComponentUser,
} from "@/lib/transformers";

import type { ApiState } from "./useApiState";

// ==================== USER HOOKS ====================

/**
 * Hook to fetch and manage list of users with client-side filtering
 */
export function useUsers(params?: { 
  q?: string;
  kyc_status?: string;
  riskCategory?: string;
  blacklisted?: boolean;
  skip?: number; 
  limit?: number;
}) {
  const [state, setState] = useState<ApiState<ComponentUser[]>>({
    data: null,
    loading: true,
    error: null,
  });

  // Stringify params for stable dependency tracking
  const paramsKey = JSON.stringify(params || {});

  const fetchUsers = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Fetch all users (backend only supports skip/limit)
      const users = await userApi.getUsers({ skip: params?.skip, limit: params?.limit || 1000 });
      let transformedUsers = users.map(user => transformApiUserToComponent(user));
      
      // Apply client-side filters
      if (params?.q) {
        const searchLower = params.q.toLowerCase();
        transformedUsers = transformedUsers.filter(user => 
          user.name.toLowerCase().includes(searchLower) ||
          user.email.toLowerCase().includes(searchLower)
        );
      }
      
      if (params?.kyc_status && params.kyc_status !== 'all') {
        const kycStatus = params.kyc_status.charAt(0).toUpperCase() + params.kyc_status.slice(1).toLowerCase();
        transformedUsers = transformedUsers.filter(user => user.kycStatus === kycStatus);
      }
      
      if (params?.riskCategory && params.riskCategory !== 'all') {
        const riskLevel = params.riskCategory.charAt(0).toUpperCase() + params.riskCategory.slice(1).toLowerCase();
        transformedUsers = transformedUsers.filter(user => user.riskLevel === riskLevel);
      }
      
      if (params?.blacklisted !== undefined) {
        transformedUsers = transformedUsers.filter(user => 
          params.blacklisted ? user.accountStatus === 'Suspended' : user.accountStatus === 'Active'
        );
      }
      
      setState({ data: transformedUsers, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch users');
      setState({ data: null, loading: false, error: err });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]); // Use stringified params for stable comparison

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  return {
    users: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchUsers,
  };
}

/**
 * Hook to fetch single user with transaction statistics
 */
export function useUser(userId: number | null) {
  const [state, setState] = useState<ApiState<ComponentUser>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchUser = useCallback(async () => {
    if (!userId) {
      setState({ data: null, loading: false, error: null });
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Fetch user data and their transaction statistics
      const user = await userApi.getUser(userId);
      
      let events: ReturnType<typeof generateUserEventsFromTransactions> = [];
      try {
        const transactionResponse = await transactionApi.getUserTransactions(userId, { limit: 20 });
        const transactions = transactionResponse.items || [];
        events = generateUserEventsFromTransactions(transactions, userId);
      } catch (txError) {
        // If transactions fail, continue with empty events
        console.warn('Failed to fetch transactions for user:', txError);
      }
      
      const transformedUser = transformApiUserToComponent(user, events);
      
      setState({ data: transformedUser, loading: false, error: null });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to fetch user');
      setState({ data: null, loading: false, error: err });
    }
  }, [userId]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return {
    user: state.data,
    loading: state.loading,
    error: state.error,
    refetch: fetchUser,
  };
}

/**
 * Hook for user management actions (suspend, update, delete)
 */
export function useUserActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const suspendUser = useCallback(async (userId: number, reason: string = 'Account suspended by admin') => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await userApi.suspendUser(userId, reason);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to suspend user');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const unsuspendUser = useCallback(async (userId: number, reason: string = 'Account restored by admin') => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await userApi.unsuspendUser(userId, reason);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to unsuspend user');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const updateUser = useCallback(async (userId: number, data: Partial<ApiUser>) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await userApi.updateUser(userId, data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to update user');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const deleteUser = useCallback(async (userId: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await userApi.deleteUser(userId);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete user');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  const createUser = useCallback(async (data: Partial<ApiUser>) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await userApi.createUser(data);
      setLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create user');
      setError(error);
      setLoading(false);
      throw error;
    }
  }, []);

  return {
    suspendUser,
    unsuspendUser,
    updateUser,
    deleteUser,
    createUser,
    loading,
    error,
  };
}
