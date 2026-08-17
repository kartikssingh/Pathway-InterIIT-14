/** Transaction ledger endpoints. */

import { apiRequest, buildQuery } from "./client";
import type { Transaction } from "./types";

/** The shape every transaction list endpoint returns. */
export interface TransactionList {
  total: number;
  items: Transaction[];
}

export const transactionApi = {
  /**
   * Get all transactions with pagination
   * Endpoint: GET /transactions
   * Returns: Individual transaction records
   */
  getTransactions: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    const endpoint = `/transactions${buildQuery(params)}`;
    return apiRequest<TransactionList>(endpoint);
  },

  /**
   * Get transactions for a specific user
   * Endpoint: GET /transactions/user/{user_id}
   */
  getUserTransactions: async (userId: number, params?: {
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    const endpoint = `/transactions/user/${userId}${buildQuery(params)}`;
    return apiRequest<TransactionList>(endpoint);
  },

  /**
   * Get single transaction by ID
   * Endpoint: GET /transactions/{transaction_id}
   */
  getTransaction: async (transactionId: number): Promise<Transaction> => {
    return apiRequest<Transaction>(`/transactions/${transactionId}`);
  },

  /**
   * Get transactions by type
   * Endpoint: GET /transactions/type/{txn_type}
   */
  getTransactionsByType: async (txnType: string, params?: {
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    const endpoint = `/transactions/type/${txnType}${buildQuery(params)}`;
    return apiRequest<TransactionList>(endpoint);
  },

  /**
   * Get fraud transactions
   * Endpoint: GET /transactions/fraud/all
   */
  getFraudTransactions: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    const endpoint = `/transactions/fraud/all${buildQuery(params)}`;
    return apiRequest<TransactionList>(endpoint);
  },

  /**
   * Filter transactions by amount range
   * Endpoint: GET /transactions/filter/amount?min_amount=100&max_amount=10000
   */
  filterTransactionsByAmount: async (params: {
    min_amount: number;
    max_amount: number;
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    return apiRequest<TransactionList>(
      `/transactions/filter/amount${buildQuery(params)}`,
    );
  },

  /**
   * Filter transactions by date range
   * Endpoint: GET /transactions/filter/date?start_date=2024-01-01&end_date=2024-01-31
   */
  filterTransactionsByDate: async (params: {
    start_date: string;
    end_date: string;
    skip?: number;
    limit?: number;
  }): Promise<TransactionList> => {
    return apiRequest<TransactionList>(
      `/transactions/filter/date${buildQuery(params)}`,
    );
  },

  /**
   * Get user transaction statistics
   * Endpoint: GET /transactions/stats/user/{user_id}
   */
  getUserTransactionStats: async (userId: number): Promise<{
    total_transactions: number;
    total_amount: number;
    fraud_count: number;
    fraud_amount: number;
    avg_amount: number;
    max_amount: number;
    min_amount: number;
  }> => {
    return apiRequest(`/transactions/stats/user/${userId}`);
  },

  /**
   * Create a new transaction
   * Endpoint: POST /transactions/add
   */
  createTransaction: async (transaction: Partial<Transaction>): Promise<Transaction> => {
    return apiRequest<Transaction>('/transactions/add', {
      method: 'POST',
      body: JSON.stringify(transaction),
    });
  },

  /**
   * Update a transaction
   * Endpoint: PATCH /transactions/{transaction_id}
   */
  updateTransaction: async (transactionId: number, updates: Partial<Transaction>): Promise<Transaction> => {
    return apiRequest<Transaction>(`/transactions/${transactionId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  /**
   * Delete a transaction
   * Endpoint: DELETE /transactions/{transaction_id}
   */
  deleteTransaction: async (transactionId: number): Promise<{ ok: boolean }> => {
    return apiRequest<{ ok: boolean }>(`/transactions/${transactionId}`, {
      method: 'DELETE',
    });
  },
};
