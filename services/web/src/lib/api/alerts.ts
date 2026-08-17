/** Compliance alert endpoints. */

import { apiRequest, buildQuery } from "./client";
import type {
  AlertDismissRequest,
  AlertDismissResponse,
  AlertTrendResponse,
  ComplianceAlert,
  ComplianceAlertListResponse,
  ComplianceAlertUpdate,
  AlertsSummaryResponse,
  CriticalAlert,
  LiveAlert,
  TopAlertsResponse,
  UnclassifiedAlertsResponse,
} from "./types";

export const alertApi = {
  /**
   * Get critical alerts for dashboard
   * Endpoint: GET /dashboard/critical-alerts
   */
  getCriticalAlerts: async (params?: {
    limit?: number;
    severity?: string;
    hours?: number;
  }): Promise<CriticalAlert[]> => {
    const endpoint = `/dashboard/critical-alerts${buildQuery(params)}`;
    return apiRequest<CriticalAlert[]>(endpoint);
  },

  /**
   * Get live alerts for real-time monitoring
   * Endpoint: GET /dashboard/live-alerts
   */
  getLiveAlerts: async (params?: {
    limit?: number;
    since?: string;
  }): Promise<LiveAlert[]> => {
    const endpoint = `/dashboard/live-alerts${buildQuery(params)}`;
    return apiRequest<LiveAlert[]>(endpoint);
  },

  /**
   * Get alert trend data for visualization
   * Endpoint: GET /dashboard/alert-trend
   */
  getAlertTrend: async (params?: {
    period?: string;
    interval?: string;
    severity?: string;
  }): Promise<AlertTrendResponse> => {
    const endpoint = `/dashboard/alert-trend${buildQuery(params)}`;
    return apiRequest<AlertTrendResponse>(endpoint);
  },

  /**
   * Dismiss an alert
   * Endpoint: POST /dashboard/alerts/{alert_id}/dismiss
   */
  dismissAlert: async (alertId: string, request?: AlertDismissRequest): Promise<AlertDismissResponse> => {
    return apiRequest<AlertDismissResponse>(`/dashboard/alerts/${alertId}/dismiss`, {
      method: 'POST',
      body: JSON.stringify(request || {}),
    });
  },

  /**
   * Get compliance alerts with filtering
   * Endpoint: GET /compliance/alerts
   */
  getComplianceAlerts: async (params?: {
    limit?: number;
    offset?: number;
    severity?: string;
    status?: string;
    alert_type?: string;
    user_id?: number;
  }): Promise<ComplianceAlertListResponse> => {
    const endpoint = `/compliance/alerts${buildQuery(params)}`;
    return apiRequest<ComplianceAlertListResponse>(endpoint);
  },

  /**
   * Get single compliance alert
   * Endpoint: GET /compliance/alerts/{alert_id}
   */
  getComplianceAlert: async (alertId: number): Promise<ComplianceAlert> => {
    return apiRequest<ComplianceAlert>(`/compliance/alerts/${alertId}`);
  },

  /**
   * Get top K most critical alerts
   * Endpoint: GET /compliance/alerts/top
   */
  getTopAlerts: async (params?: {
    k?: number;
    status?: string;
  }): Promise<TopAlertsResponse> => {
    const endpoint = `/compliance/alerts/top${buildQuery(params)}`;
    return apiRequest<TopAlertsResponse>(endpoint);
  },

  /**
   * Update compliance alert
   * Endpoint: PATCH /compliance/alerts/{alert_id}
   */
  updateComplianceAlert: async (alertId: number, update: ComplianceAlertUpdate): Promise<ComplianceAlert> => {
    return apiRequest<ComplianceAlert>(`/compliance/alerts/${alertId}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    });
  },

  /**
   * Acknowledge a compliance alert
   * Endpoint: POST /compliance/alerts/{alert_id}/acknowledge
   */
  acknowledgeComplianceAlert: async (alertId: number): Promise<{
    success: boolean;
    alert_id: number;
    acknowledged_at: string;
    acknowledged_by: string;
  }> => {
    return apiRequest(`/compliance/alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  },

  /**
   * Resolve a compliance alert (confirmed issue addressed)
   * Endpoint: POST /compliance/alerts/{alert_id}/resolve
   */
  resolveComplianceAlert: async (alertId: number, notes?: string): Promise<{
    success: boolean;
    message: string;
    alert_id: number;
    status: string;
    resolved_at: string;
    resolved_by: string;
  }> => {
    const params = notes ? `?notes=${encodeURIComponent(notes)}` : '';
    return apiRequest(`/compliance/alerts/${alertId}/resolve${params}`, {
      method: 'POST',
    });
  },

  /**
   * Dismiss a compliance alert (false positive / not actionable)
   * Endpoint: POST /compliance/alerts/{alert_id}/dismiss
   */
  dismissComplianceAlert: async (alertId: number, reason?: string): Promise<{
    success: boolean;
    message: string;
    alert_id: number;
    status: string;
    dismissed_at: string;
    dismissed_by: string;
    reason: string;
  }> => {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    return apiRequest(`/compliance/alerts/${alertId}/dismiss${params}`, {
      method: 'POST',
    });
  },

  /**
   * Get compliance alert statistics
   * Endpoint: GET /compliance/alerts/stats/summary
   */
  getComplianceAlertStats: async (): Promise<AlertsSummaryResponse> => {
    return apiRequest<AlertsSummaryResponse>('/compliance/alerts/stats/summary');
  },

  /**
   * Get unclassified alerts (alerts pending review)
   * Endpoint: GET /dashboard/alerts/unclassified
   * Returns active/investigating alerts
   */
  getUnclassifiedAlerts: async (params?: {
    limit?: number;
    skip?: number;
    severity?: string;
    status?: string;
  }): Promise<UnclassifiedAlertsResponse> => {
    const endpoint = `/dashboard/alerts/unclassified${buildQuery(params)}`;
    return apiRequest<UnclassifiedAlertsResponse>(endpoint);
  },
};
