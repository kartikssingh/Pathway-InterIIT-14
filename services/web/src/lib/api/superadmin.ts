/** Superadmin: audit logs, metrics, health checks and system alerts. */

import { apiRequest, buildQuery } from "./client";

export interface CreateAdminRequest {
  username: string;
  email: string;
  password: string;
  role: 'admin' | 'superadmin';
}

export interface CreateAdminResponse {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
  updated_at?: string;
}

export interface AuditLog {
  id: number;
  admin_id: number;
  admin_username: string | null;
  action_type: string;
  action_description: string;
  target_type: string | null;
  target_id: number | null;
  target_identifier: string | null;
  action_metadata: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  total: number;
  logs: AuditLog[];
  limit: number;
  offset: number;
}

export interface AdminListItem {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
  updated_at?: string;
  last_login_at: string | null;
}

// ==================== SUPERADMIN MONITORING API ====================

export interface MetricsSummary {
  resolution_rate: number;       // 0-100 (percentage of resolved alerts)
  avg_response_time_ms: number;  // >= 0 (milliseconds)
  api_error_rate: number;        // 0-100 (percentage)
  total_alerts: number;          // >= 0
  resolved: number;              // >= 0 (acknowledged alerts)
  unresolved: number;            // >= 0 (pending alerts)
  period_start: string;          // ISO datetime
  period_end: string;            // ISO datetime
}

export interface SystemAlert {
  id: number;
  alert_type: string;
  title: string;
  description: string;
  severity: 'critical' | 'error' | 'warning' | 'info';
  component: string | null;
  metric_type: string | null;
  threshold_value: string | null;
  actual_value: string | null;
  alert_data: Record<string, any> | null;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  triggered_at: string;
  last_updated: string;
  notifications_sent: number;
}

export interface HealthCheck {
  id: number;
  check_type: string;
  component_name: string;
  status: 'healthy' | 'degraded' | 'failed' | 'recovering';
  severity: 'info' | 'warning' | 'error' | 'critical';
  error_type: string | null;
  error_message: string | null;
  request_context: Record<string, any> | null;
  response_context: Record<string, any> | null;
  response_time_ms: number | null;
  retry_count: number;
  affected_operations: string[] | null;
  user_impact: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  resolution_notes: string | null;
  auto_recovered: boolean;
  detected_at: string;
  last_occurrence: string;
  alert_sent: boolean;
}

// Compliance alert summary (fraud/AML alerts) for superadmin dashboard
export interface ComplianceAlertSummary {
  id: number;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string | null;
  user_id: number | null;
  user_name: string | null;
  status: 'active' | 'investigating' | 'resolved' | 'dismissed' | 'escalated';
  priority: string | null;
  is_acknowledged: boolean;
  created_at: string;
  triggered_at: string | null;
}

export interface SuperadminDashboard {
  metrics_summary: MetricsSummary;
  unresolved_compliance_alerts: ComplianceAlertSummary[];
  active_system_alerts: SystemAlert[];
  recent_health_issues: HealthCheck[];
  recent_audit_logs: AuditLog[];
  system_status: 'healthy' | 'degraded' | 'critical';
}

export interface MetricHistory {
  id: number;
  metric_type: string;
  metric_category: string;
  metric_value: number;
  metric_unit: string;
  time_window: string;
  aggregation_period_start: string;
  aggregation_period_end: string;
  details: Record<string, any> | null;
  total_count: number | null;
  positive_count: number | null;
  negative_count: number | null;
  recorded_at: string;
  is_anomaly: boolean;
  anomaly_threshold: number | null;
}

export interface AlertResolutionStats {
  total_alerts: number;              // >= 0
  resolved: number;                  // >= 0 (acknowledged alerts)
  unresolved: number;                // >= 0 (pending alerts)
  escalated: number;                 // >= 0
  avg_resolution_time_hours: number; // >= 0
}

export interface AdminActivity {
  admin_id: number;
  admin_username: string;
  total_actions: number;
  alerts_reviewed: number;
  users_flagged: number;
  decisions_made: number;
  last_active: string;
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'critical';
  critical_alerts: number;
  unresolved_errors: number;
  checked_at: string;
}

export interface UpdateHealthCheckRequest {
  status?: 'healthy' | 'degraded' | 'failed' | 'recovering';
  is_resolved?: boolean;
  resolution_notes?: string;
}

export interface UpdateSystemAlertRequest {
  status?: 'active' | 'acknowledged' | 'resolved';
  acknowledged_by?: string;
  resolution_notes?: string;
}

export const superadminApi = {
  /**
   * Create a new admin account (Superadmin only)
   * Endpoint: POST /api/auth/superadmin/create-admin
   */
  createAdmin: async (data: CreateAdminRequest): Promise<CreateAdminResponse> => {
    return apiRequest<CreateAdminResponse>('/api/auth/superadmin/create-admin', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get audit logs (Superadmin only)
   * Endpoint: GET /api/auth/superadmin/logs
   */
  getAuditLogs: async (params?: {
    admin_id?: number;
    action_type?: string;
    target_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditLogsResponse> => {
    const endpoint = `/api/auth/superadmin/logs${buildQuery(params)}`;
    return apiRequest<AuditLogsResponse>(endpoint);
  },

  /**
   * List all admin accounts (Superadmin only)
   * Endpoint: GET /api/auth/superadmin/admins
   */
  listAdmins: async (): Promise<AdminListItem[]> => {
    const response = await apiRequest<{ admins: AdminListItem[] }>('/api/auth/superadmin/admins');
    return response.admins;
  },

  // ==================== MONITORING API ====================

  /**
   * Get complete superadmin dashboard
   * Endpoint: GET /api/superadmin/dashboard
   */
  getDashboard: async (days: number = 7): Promise<SuperadminDashboard> => {
    return apiRequest<SuperadminDashboard>(`/api/superadmin/dashboard?days=${days}`);
  },

  /**
   * Get superadmin audit logs with filters
   * Endpoint: GET /api/superadmin/audit-logs
   */
  getMonitoringAuditLogs: async (params?: {
    admin_id?: number;
    action_type?: string;
    target_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditLog[]> => {
    const endpoint = `/api/superadmin/audit-logs${buildQuery(params)}`;
    return apiRequest<AuditLog[]>(endpoint);
  },

  /**
   * Get specific audit log
   * Endpoint: GET /api/superadmin/audit-logs/{audit_id}
   */
  getAuditLog: async (auditId: number): Promise<AuditLog> => {
    return apiRequest<AuditLog>(`/api/superadmin/audit-logs/${auditId}`);
  },

  /**
   * Get metrics summary
   * Endpoint: GET /api/superadmin/metrics/summary
   */
  getMetricsSummary: async (days: number = 7): Promise<MetricsSummary> => {
    return apiRequest<MetricsSummary>(`/api/superadmin/metrics/summary?days=${days}`);
  },

  /**
   * Get metrics history
   * Endpoint: GET /api/superadmin/metrics/history
   */
  getMetricsHistory: async (params?: {
    metric_type?: string;
    metric_category?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<MetricHistory[]> => {
    const endpoint = `/api/superadmin/metrics/history${buildQuery(params)}`;
    return apiRequest<MetricHistory[]>(endpoint);
  },

  /**
   * Get alert resolution statistics
   * Endpoint: GET /api/superadmin/metrics/alert-resolutions
   */
  getAlertResolutions: async (days: number = 30): Promise<AlertResolutionStats> => {
    return apiRequest<AlertResolutionStats>(`/api/superadmin/metrics/alert-resolutions?days=${days}`);
  },

  /**
   * Get admin activity statistics
   * Endpoint: GET /api/superadmin/metrics/admin-activity
   */
  getAdminActivity: async (days: number = 30): Promise<AdminActivity[]> => {
    return apiRequest<AdminActivity[]>(`/api/superadmin/metrics/admin-activity?days=${days}`);
  },

  /**
   * Get health checks
   * Endpoint: GET /api/superadmin/health/checks
   */
  getHealthChecks: async (params?: {
    check_type?: string;
    component_name?: string;
    status?: string;
    severity?: string;
    is_resolved?: boolean;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<HealthCheck[]> => {
    const endpoint = `/api/superadmin/health/checks${buildQuery(params)}`;
    return apiRequest<HealthCheck[]>(endpoint);
  },

  /**
   * Update health check
   * Endpoint: PATCH /api/superadmin/health/checks/{health_id}
   */
  updateHealthCheck: async (healthId: number, data: UpdateHealthCheckRequest): Promise<HealthCheck> => {
    return apiRequest<HealthCheck>(`/api/superadmin/health/checks/${healthId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get system alerts
   * Endpoint: GET /api/superadmin/alerts
   */
  getSystemAlerts: async (params?: {
    alert_type?: string;
    status?: string;
    severity?: string;
    component?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<SystemAlert[]> => {
    const endpoint = `/api/superadmin/alerts${buildQuery(params)}`;
    return apiRequest<SystemAlert[]>(endpoint);
  },

  /**
   * Update system alert
   * Endpoint: PATCH /api/superadmin/alerts/{alert_id}
   */
  updateSystemAlert: async (alertId: number, data: UpdateSystemAlertRequest): Promise<SystemAlert> => {
    return apiRequest<SystemAlert>(`/api/superadmin/alerts/${alertId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get system status
   * Endpoint: GET /api/superadmin/system-status
   */
  getSystemStatus: async (): Promise<SystemStatus> => {
    return apiRequest<SystemStatus>('/api/superadmin/system-status');
  },
};
