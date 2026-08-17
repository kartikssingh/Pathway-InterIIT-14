"use client";

import { useSuperadminDashboard, useSystemAlertActions, useSystemAlerts } from "@/hooks/useApi";
import { MetricCard } from "@/components/MetricCard";
import { SystemAlertCard } from "@/components/SystemAlertCard";
import { HealthStatusCard } from "@/components/HealthStatusCard";
import { StatusBadge } from "@/components/StatusBadge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ArrowRight,
  User,
  Shield,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

// Severity color mapping for compliance alerts
const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

const severityBorderColors: Record<string, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-blue-500',
};

export default function SuperadminDashboardPage() {
  const days = 7; // Fixed period for dashboard
  const { dashboard, loading, error, refetch } = useSuperadminDashboard(days);
  const { updateSystemAlert } = useSystemAlertActions();
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);
  
  // Fetch all system alerts
  const { systemAlerts: rawSystemAlerts, loading: alertsLoading, refetch: refetchAlerts } = useSystemAlerts({
    limit: 1000,
  });
  
  // Separate unresolved and resolved system alerts
  const unresolvedSystemAlerts = rawSystemAlerts?.filter(alert => alert.status !== 'resolved') || [];
  const resolvedSystemAlerts = rawSystemAlerts?.filter(alert => alert.status === 'resolved') || [];

  const handleAcknowledgeSystemAlert = async (alertId: number) => {
    setUpdatingAlertId(alertId);
    try {
      await updateSystemAlert(alertId, {
        status: 'acknowledged',
        resolution_notes: 'Alert acknowledged by superadmin'
      });
      refetch();
      refetchAlerts();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      alert(`Failed to acknowledge alert: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const handleResolveSystemAlert = async (alertId: number) => {
    setUpdatingAlertId(alertId);
    try {
      await updateSystemAlert(alertId, {
        status: 'resolved',
        resolution_notes: 'Alert resolved by superadmin'
      });
      refetch();
      refetchAlerts();
    } catch (err) {
      console.error('Failed to resolve alert:', err);
      alert(`Failed to resolve alert: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  if (loading && !dashboard) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Dashboard</h3>
              <p className="text-sm text-red-700 mt-1">{error.message}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const { 
    metrics_summary, 
    unresolved_compliance_alerts = [], 
    active_system_alerts, 
    recent_health_issues, 
    recent_audit_logs, 
    system_status 
  } = dashboard;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Superadmin Dashboard</h1>
          <p className="text-gray-600 mt-1">Compliance monitoring and alert management</p>
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={refetch} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* System Status Banner */}
      <Card className={`p-6 border-2 ${
        system_status === 'healthy' ? 'border-green-200 bg-green-50' :
        system_status === 'degraded' ? 'border-yellow-200 bg-yellow-50' :
        'border-red-200 bg-red-50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {system_status === 'healthy' ? (
              <CheckCircle className="h-8 w-8 text-green-600" />
            ) : (
              <AlertTriangle className="h-8 w-8 text-red-600" />
            )}
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                System Status: <span className="capitalize">{system_status}</span>
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {metrics_summary.unresolved} unresolved compliance alerts, {active_system_alerts.length} active system alerts
              </p>
            </div>
          </div>
          <StatusBadge status={system_status} />
        </div>
      </Card>

      {/* Compliance Alert Metrics */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Compliance Alert Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Resolution Rate"
            value={metrics_summary.resolution_rate.toFixed(1)}
            unit="%"
            icon={TrendingUp}
            severity={metrics_summary.resolution_rate >= 70 ? 'success' : metrics_summary.resolution_rate >= 50 ? 'warning' : 'error'}
          />
          <MetricCard
            title="API Error Rate"
            value={metrics_summary.api_error_rate.toFixed(1)}
            unit="%"
            icon={TrendingDown}
            severity={metrics_summary.api_error_rate <= 1 ? 'success' : metrics_summary.api_error_rate <= 5 ? 'warning' : 'error'}
          />
          <MetricCard
            title="Total Alerts"
            value={metrics_summary.total_alerts.toString()}
            unit=""
            icon={Activity}
            severity="info"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Resolved Alerts</p>
            <p className="text-2xl font-bold text-green-600">{metrics_summary.resolved}</p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Unresolved Alerts</p>
            <p className="text-2xl font-bold text-yellow-600">{metrics_summary.unresolved}</p>
          </Card>
        </div>
      </div>

      {/* Main Content: Compliance Alerts (Primary) */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <Shield className="h-6 w-6 text-purple-600" />
            Unresolved Compliance Alerts
          </h2>
          <Link href="/main/compliance">
            <Button variant="outline" size="sm">
              View All <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </div>

        {unresolved_compliance_alerts.length === 0 ? (
          <Card className="p-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <p className="text-gray-500 text-lg">No unresolved compliance alerts</p>
            <p className="text-gray-400 text-sm mt-1">All compliance alerts have been reviewed</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {unresolved_compliance_alerts.map((alert) => (
              <Card 
                key={alert.id} 
                className={`p-4 border-l-4 ${severityBorderColors[alert.severity] || 'border-l-gray-500'} hover:shadow-md transition-shadow`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${severityColors[alert.severity] || 'bg-gray-100 text-gray-800'}`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                        {alert.alert_type.replace(/_/g, ' ')}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        alert.status === 'active' ? 'bg-red-100 text-red-700' :
                        alert.status === 'investigating' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {alert.status}
                      </span>
                    </div>
                    <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                    {alert.description && (
                      <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      {alert.user_name && (
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {alert.user_name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(alert.triggered_at || alert.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <Link href={`/main/compliance?alert=${alert.id}`}>
                    <Button variant="outline" size="sm">
                      Review
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Two Column Layout for System Alerts and Health Issues */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Alerts (Secondary - Bottom Right) */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">System Alerts</h2>
            <Button onClick={refetchAlerts} variant="ghost" size="sm" disabled={alertsLoading}>
              <RefreshCw className={`h-4 w-4 ${alertsLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {rawSystemAlerts && rawSystemAlerts.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-gray-500">No system alerts</p>
            </Card>
          ) : (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {/* Unresolved System Alerts */}
              {unresolvedSystemAlerts.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    Unresolved ({unresolvedSystemAlerts.length})
                  </h3>
                  <div className="space-y-2">
                    {unresolvedSystemAlerts.slice(0, 5).map((alert) => (
                      <SystemAlertCard
                        key={alert.id}
                        alert={alert}
                        onAcknowledge={updatingAlertId === alert.id ? undefined : handleAcknowledgeSystemAlert}
                        onResolve={updatingAlertId === alert.id ? undefined : handleResolveSystemAlert}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Resolved System Alerts */}
              {resolvedSystemAlerts.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Resolved ({resolvedSystemAlerts.length})
                  </h3>
                  <div className="space-y-2">
                    {resolvedSystemAlerts.slice(0, 3).map((alert) => (
                      <SystemAlertCard
                        key={alert.id}
                        alert={alert}
                        onAcknowledge={updatingAlertId === alert.id ? undefined : handleAcknowledgeSystemAlert}
                        onResolve={updatingAlertId === alert.id ? undefined : handleResolveSystemAlert}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Health Issues */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Health Issues</h2>
          </div>

          {recent_health_issues.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-gray-500">No health issues</p>
            </Card>
          ) : (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {/* Unresolved Health Issues */}
              {recent_health_issues.filter(h => !h.is_resolved).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    Unresolved ({recent_health_issues.filter(h => !h.is_resolved).length})
                  </h3>
                  <div className="space-y-2">
                    {recent_health_issues.filter(h => !h.is_resolved).slice(0, 5).map((health) => (
                      <HealthStatusCard
                        key={health.id}
                        healthCheck={health}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Resolved Health Issues */}
              {recent_health_issues.filter(h => h.is_resolved).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Resolved ({recent_health_issues.filter(h => h.is_resolved).length})
                  </h3>
                  <div className="space-y-2">
                    {recent_health_issues.filter(h => h.is_resolved).slice(0, 3).map((health) => (
                      <HealthStatusCard
                        key={health.id}
                        healthCheck={health}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent Audit Logs */}
      {recent_audit_logs.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Recent Audit Logs</h2>
            <Link href="/main/superadmin/audit-logs">
              <Button variant="outline" size="sm">
                View All <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </div>
          <Card>
            <div className="divide-y divide-gray-200">
              {recent_audit_logs.slice(0, 5).map((log) => (
                <div key={log.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">
                        {log.action_description}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        by {log.admin_username || 'System'} • {new Date(log.created_at).toLocaleString()}
                      </p>
                    </div>
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded">
                      {log.action_type.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Quick Links */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Links</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link href="/main/superadmin/metrics">
            <Button variant="outline" className="w-full">
              <Activity className="h-4 w-4 mr-2" />
              Metrics
            </Button>
          </Link>
          <Link href="/main/superadmin/audit-logs">
            <Button variant="outline" className="w-full">
              <Clock className="h-4 w-4 mr-2" />
              Audit Logs
            </Button>
          </Link>
          <Link href="/main/superadmin/health">
            <Button variant="outline" className="w-full">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Health Checks
            </Button>
          </Link>
          <Link href="/main/superadmin/alerts">
            <Button variant="outline" className="w-full">
              <AlertTriangle className="h-4 w-4 mr-2" />
              System Alerts
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
