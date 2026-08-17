"use client";

import { useSystemAlerts, useSystemAlertActions } from "@/hooks/useApi";
import { SystemAlertCard } from "@/components/SystemAlertCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import { useState } from "react";

export default function SystemAlertsPage() {
  const { systemAlerts, loading, error, refetch } = useSystemAlerts({
    limit: 1000,
  });

  const { updateSystemAlert } = useSystemAlertActions();
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);

  const handleAcknowledge = async (alertId: number) => {
    setUpdatingAlertId(alertId);
    try {
      await updateSystemAlert(alertId, {
        status: 'acknowledged',
        acknowledged_by: 'superadmin',
        resolution_notes: 'Alert acknowledged by superadmin'
      });
      await refetch();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const handleResolve = async (alertId: number) => {
    setUpdatingAlertId(alertId);
    try {
      await updateSystemAlert(alertId, {
        status: 'resolved',
        resolution_notes: 'Alert resolved by superadmin'
      });
      await refetch();
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  // Separate unresolved and resolved alerts
  const unresolvedAlerts = systemAlerts?.filter(a => a.status !== 'resolved') || [];
  const resolvedAlerts = systemAlerts?.filter(a => a.status === 'resolved') || [];

  // Statistics
  const activeCount = unresolvedAlerts.filter(a => a.status === 'active').length;
  const criticalCount = unresolvedAlerts.filter(a => a.severity === 'critical').length;
  const acknowledgedCount = unresolvedAlerts.filter(a => a.status === 'acknowledged').length;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Alerts</h1>
          <p className="text-gray-600 mt-1">Monitor and manage system-level alerts and anomalies</p>
        </div>
        <Button onClick={refetch} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-600 mb-1">Total Alerts</p>
          <p className="text-2xl font-bold text-gray-900">{systemAlerts?.length || 0}</p>
        </Card>
        <Card className="p-4 border-2 border-orange-200 bg-orange-50">
          <p className="text-sm text-gray-600 mb-1">Active Alerts</p>
          <p className="text-2xl font-bold text-orange-600">{activeCount}</p>
        </Card>
        <Card className="p-4 border-2 border-red-200 bg-red-50">
          <p className="text-sm text-gray-600 mb-1">Critical Active</p>
          <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-600 mb-1">Acknowledged</p>
          <p className="text-2xl font-bold text-blue-600">{acknowledgedCount}</p>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="p-6 bg-red-50 border-red-200">
          <p className="text-red-800">{error.message}</p>
        </Card>
      )}

      {/* System Alerts List */}
      {loading && !systemAlerts ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : systemAlerts && systemAlerts.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-gray-500">No system alerts found</p>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Unresolved Alerts */}
          {unresolvedAlerts.length > 0 && (
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-3 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                Unresolved ({unresolvedAlerts.length})
              </h2>
              <div className="space-y-4">
                {unresolvedAlerts.map((alert) => (
                  <SystemAlertCard
                    key={alert.id}
                    alert={alert}
                    onAcknowledge={updatingAlertId === alert.id ? undefined : handleAcknowledge}
                    onResolve={updatingAlertId === alert.id ? undefined : handleResolve}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Resolved Alerts */}
          {resolvedAlerts.length > 0 && (
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-3 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Resolved ({resolvedAlerts.length})
              </h2>
              <div className="space-y-4">
                {resolvedAlerts.map((alert) => (
                  <SystemAlertCard
                    key={alert.id}
                    alert={alert}
                    onAcknowledge={updatingAlertId === alert.id ? undefined : handleAcknowledge}
                    onResolve={updatingAlertId === alert.id ? undefined : handleResolve}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
