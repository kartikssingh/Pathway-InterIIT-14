/** Per-user risk history and sanctions screening records. */

import { apiRequest, buildQuery } from "./client";
import type {
  CreateToxicityHistoryRequest,
  CreateUserSanctionMatchRequest,
  ToxicityHistory,
  UserSanctionMatch,
} from "./types";

export const toxicityHistoryApi = {
  /**
   * Get toxicity history for a specific user
   * Endpoint: GET /users/{user_id}/toxicity-history
   */
  getToxicityHistory: async (userId: number, params?: {
    skip?: number;
    limit?: number;
  }): Promise<ToxicityHistory[]> => {
    const endpoint = `/users/${userId}/toxicity-history${buildQuery(params)}`;
    return apiRequest<ToxicityHistory[]>(endpoint);
  },

  /**
   * Create a new toxicity history record
   * Endpoint: POST /users/{user_id}/toxicity-history
   */
  createToxicityHistory: async (userId: number, data: CreateToxicityHistoryRequest): Promise<ToxicityHistory> => {
    return apiRequest<ToxicityHistory>(`/users/${userId}/toxicity-history`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ==================== USER SANCTION MATCHES API ====================

export const userSanctionMatchApi = {
  /**
   * Get sanction match history for a specific user
   * Endpoint: GET /users/{user_id}/sanction-matches
   */
  getSanctionMatches: async (userId: number, params?: {
    skip?: number;
    limit?: number;
  }): Promise<UserSanctionMatch[]> => {
    const endpoint = `/users/${userId}/sanction-matches${buildQuery(params)}`;
    return apiRequest<UserSanctionMatch[]>(endpoint);
  },

  /**
   * Create a new sanction match record
   * Endpoint: POST /users/{user_id}/sanction-matches
   */
  createSanctionMatch: async (userId: number, data: CreateUserSanctionMatchRequest): Promise<UserSanctionMatch> => {
    return apiRequest<UserSanctionMatch>(`/users/${userId}/sanction-matches`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
