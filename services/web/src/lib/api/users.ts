/** User and KYC endpoints. */

import { apiRequest, buildQuery, requestMultipart } from "./client";
import type { User } from "./types";

export const userApi = {
  /**
   * Get all users with pagination
   * Endpoints: GET /users or GET /user/all
   * Note: Backend only supports skip and limit. Other filtering is done client-side.
   */
  getUsers: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<User[]> => {
    const endpoint = `/users${buildQuery(params)}`;
    return apiRequest<User[]>(endpoint);
  },

  /**
   * Get single user by ID
   * Endpoint: GET /users/{user_id}
   */
  getUser: async (userId: number): Promise<User> => {
    return apiRequest<User>(`/users/${userId}`);
  },

  /**
   * Create new user
   * Endpoint: POST /users
   */
  createUser: async (userData: Partial<User>): Promise<User> => {
    return apiRequest<User>('/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  /**
   * Update user (partial update)
   * Endpoint: PATCH /users/{user_id}
   */
  updateUser: async (userId: number, userData: Partial<User>): Promise<User> => {
    return apiRequest<User>(`/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(userData),
    });
  },

  /**
   * Delete user
   * Endpoint: DELETE /users/{user_id}
   */
  deleteUser: async (userId: number): Promise<{ ok: boolean }> => {
    return apiRequest<{ ok: boolean }>(`/users/${userId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Suspend user (blacklist)
   * Endpoint: POST /user/{user_id}/blacklist
   * Requires: Admin authentication and reason parameter
   */
  suspendUser: async (userId: number, reason: string = 'Account suspended by admin'): Promise<User> => {
    const encodedReason = encodeURIComponent(reason);
    return apiRequest<User>(`/user/${userId}/blacklist?reason=${encodedReason}`, {
      method: 'POST',
    });
  },

  /**
   * Unsuspend user (remove from blacklist)
   * Endpoint: POST /user/{user_id}/whitelist
   * Requires: Admin authentication and reason parameter
   */
  unsuspendUser: async (userId: number, reason: string = 'Account restored by admin'): Promise<User> => {
    const encodedReason = encodeURIComponent(reason);
    return apiRequest<User>(`/user/${userId}/whitelist?reason=${encodedReason}`, {
      method: 'POST',
    });
  },

  /**
   * Upload PDF KYC form with automatic data extraction
   * Endpoint: POST /user/upload-form
   * Requires: Admin authentication (require_admin)
   */
  uploadPdfForm: async (
    file: File,
  ): Promise<{
    ok: boolean;
    key: string;
    url: string | null;
    filename: string;
    file_size: number;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    // The Content-Type header is deliberately not set: the browser has to add
    // the multipart boundary itself.
    return requestMultipart("/user/upload-form", formData);
  },

  /**
   * Get users by risk category
   * Endpoint: GET /user/risk/{risk_category}
   */
  getUsersByRiskCategory: async (riskCategory: string, params?: {
    skip?: number;
    limit?: number;
  }): Promise<User[]> => {
    const endpoint = `/user/risk/${riskCategory}${buildQuery(params)}`;
    return apiRequest<User[]>(endpoint);
  },

  /**
   * Get blacklisted users
   * Endpoint: GET /user/blacklisted/all
   */
  getBlacklistedUsers: async (params?: {
    skip?: number;
    limit?: number;
  }): Promise<User[]> => {
    const endpoint = `/user/blacklisted/all${buildQuery(params)}`;
    return apiRequest<User[]>(endpoint);
  },
};
