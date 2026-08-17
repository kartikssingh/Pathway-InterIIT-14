/**
 * Barrel for the API layer.
 *
 * `@/lib/api` used to resolve to a single 1,700-line file. It now resolves to
 * this directory, so every existing `import { userApi } from "@/lib/api"` keeps
 * working while the implementation lives in focused modules.
 *
 *   client.ts        fetch wrapper: auth, retries, timeouts, error parsing
 *   types.ts         shared request/response types
 *   users.ts         /users, /user
 *   transactions.ts  /transactions
 *   dashboard.ts     /dashboard aggregates
 *   alerts.ts        /compliance + /dashboard alert endpoints
 *   risk-history.ts  toxicity history and sanction matches
 *   auth.ts          /api/auth and the browser session
 *   superadmin.ts    /superadmin
 */

export * from "./types";

export {
  API_BASE_URL,
  ApiError,
  apiRequest,
  buildQuery,
  checkApiHealth,
  clearSession,
  getToken,
  requestMultipart,
  storeSession,
} from "./client";
export type { FieldError, QueryValue, RequestOptions } from "./client";

export { userApi } from "./users";
export { transactionApi } from "./transactions";
export { dashboardApi } from "./dashboard";
export { alertApi } from "./alerts";
export { toxicityHistoryApi, userSanctionMatchApi } from "./risk-history";
export { authApi } from "./auth";
export type { AdminInfo, AdminRole, LoginResponse } from "./auth";
export * from "./superadmin";

/**
 * Formatting helpers used to live in this module. They are re-exported so
 * existing imports keep resolving; new code should import from `@/lib/format`.
 */
export {
  formatCompactCurrency,
  formatCurrency,
  formatDate,
  formatDateOnly,
  formatNumber,
  formatRelativeTime,
  formatRiskScore,
  getRiskCategory,
  getRiskColor,
  humanise,
  maskIdentifier,
} from "../format";
export type { RiskCategory } from "../format";
