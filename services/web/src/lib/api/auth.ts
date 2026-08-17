/**
 * Authentication and the browser-side session.
 *
 * The session keys were read and written with raw `localStorage` calls in five
 * places across two files; they now go through the client's session helpers, so
 * there is exactly one definition of what "signed in" means.
 */

import { apiRequest, clearSession, getToken, storeSession } from "./client";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: AdminRole;
  username: string;
}

export type AdminRole = "admin" | "superadmin";

export interface AdminInfo {
  id: number;
  username: string;
  email: string;
  role: AdminRole;
  created_at: string;
  updated_at?: string;
  last_login_at: string | null;
}

const ROLE_KEY = "user_role";
const USERNAME_KEY = "username";

const readLocal = (key: string): string | null =>
  typeof window === "undefined" ? null : localStorage.getItem(key);

export const authApi = {
  /**
   * Sign in. `POST /api/auth/login` takes an OAuth2 password form, not JSON.
   */
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const form = new URLSearchParams({ username, password });

    const data = await apiRequest<LoginResponse>("/api/auth/login", {
      method: "POST",
      anonymous: true,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
      retries: 0,
    });

    storeSession(data.access_token, data.role, data.username);
    return data;
  },

  /** Sign out. The local session is cleared even if the server call fails. */
  logout: async (): Promise<void> => {
    try {
      await apiRequest("/api/auth/logout", { method: "POST", retries: 0 });
    } catch {
      // A failed logout call must never leave the browser holding a token.
    } finally {
      clearSession();
    }
  },

  /** The signed-in administrator. */
  getCurrentAdmin: async (): Promise<AdminInfo> => apiRequest<AdminInfo>("/api/auth/me"),

  isAuthenticated: (): boolean => Boolean(getToken()),

  getToken,

  getRole: (): AdminRole | null => readLocal(ROLE_KEY) as AdminRole | null,

  getUsername: (): string | null => readLocal(USERNAME_KEY),

  isSuperadmin: (): boolean => authApi.getRole() === "superadmin",
};
