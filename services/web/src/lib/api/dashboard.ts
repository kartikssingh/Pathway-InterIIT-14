/** Aggregates for the operator dashboard. */

import { apiRequest, buildQuery } from "./client";
import type { DashboardSummary, FlaggedTransaction, RiskDistribution } from "./types";

export const dashboardApi = {
  /**
   * Get dashboard summary statistics
   * Endpoint: GET /dashboard/summary
   * Note: total_transactions now uses a 30-day window (changed from 7-day)
   * RPS scores (average_i360_score, average_i_not_score) are returned in 0-1 format (display as-is)
   */
  getSummary: async (): Promise<DashboardSummary> => {
    return apiRequest<DashboardSummary>('/dashboard/summary');
  },

  /**
   * Get risk distribution across user base
   * Endpoint: GET /dashboard/risk-distribution
   */
  getRiskDistribution: async (): Promise<RiskDistribution> => {
    return apiRequest<RiskDistribution>('/dashboard/risk-distribution');
  },

  /**
   * Get flagged transactions (suspicious_score > 50)
   * Endpoint: GET /dashboard/flagged-transactions
   */
  getFlaggedTransactions: async (limit?: number): Promise<FlaggedTransaction[]> => {
    const params = buildQuery({ limit });
    return apiRequest<FlaggedTransaction[]>(`/dashboard/flagged-transactions${params}`);
  },
};
