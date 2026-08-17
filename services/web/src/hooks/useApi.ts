/**
 * Barrel for the data hooks.
 *
 * This file used to be a single 1,500-line module holding every hook in the
 * application. The hooks now live in one module per domain; re-exporting them
 * here keeps every existing `import { useUsers } from "@/hooks/useApi"` working.
 *
 *   useApiState.ts      the shared request-state primitive
 *   useUsers.ts         users and user actions
 *   useTransactions.ts  the transaction ledger
 *   useDashboard.ts     dashboard aggregates
 *   useAlerts.ts        compliance alerts
 *   useRiskHistory.ts   toxicity history and sanction matches
 *   useSuperadmin.ts    superadmin monitoring
 *
 * New code should import from the specific module.
 */

export { useApiState } from "./useApiState";
export { describeError, isRetryable } from "./useApiState";
export type { ApiState, UseApiStateOptions } from "./useApiState";

export { useUser, useUserActions, useUsers } from "./useUsers";

export {
  useTransaction,
  useTransactionActions,
  useTransactions,
  useUserTransactionStats,
} from "./useTransactions";

export { useDashboard, useFlaggedTransactions, useRiskDistribution } from "./useDashboard";

export {
  useAlertActions,
  useAlertTrend,
  useComplianceAlerts,
  useCriticalAlerts,
  useLiveAlerts,
  useUnclassifiedAlerts,
} from "./useAlerts";

export {
  useToxicityHistory,
  useToxicityHistoryActions,
  useUserSanctionMatchActions,
  useUserSanctionMatches,
} from "./useRiskHistory";

export {
  useAdminActivity,
  useAlertResolutions,
  useHealthCheckActions,
  useHealthChecks,
  useMetricsHistory,
  useMetricsSummary,
  useSuperadminAuditLogs,
  useSuperadminDashboard,
  useSystemAlertActions,
  useSystemAlerts,
  useSystemStatus,
} from "./useSuperadmin";

export { useHealthCheck } from "./useHealthCheck";
