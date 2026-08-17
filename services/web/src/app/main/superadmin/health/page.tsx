"use client";

import { useHealthChecks, useHealthCheckActions } from "@/hooks/useApi";
import { HealthStatusCard } from "@/components/HealthStatusCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import { useState } from "react";

export default function HealthChecksPage() {
  const { healthChecks, loading, error, refetch } = useHealthChecks({
    limit: 1000,
  });

  const { updateHealthCheck } = useHealthCheckActions();
  const [updatingHealthId, setUpdatingHealthId] = useState<number | null>(null);

  const handleResolve = async (healthId: number) => {
    setUpdatingHealthId(healthId);
    try {
      await updateHealthCheck(healthId, {
        is_resolved: true,
        resolution_notes: 'Issue resolved by superadmin'
      });
      await refetch();
    } catch (err) {
      console.error('Failed to resolve health check:', err);
    } finally {
      setUpdatingHealthId(null);
    }
  };

  // Separate unresolved and resolved health checks
  const unresolvedHealthChecks = healthChecks?.filter(h => !h.is_resolved) || [];
  const resolvedHealthChecks = healthChecks?.filter(h => h.is_resolved) || [];

  // Statistics
  const criticalCount = unresolvedHealthChecks.filter(h => h.severity === 'critical').length;
  const apiHealthCount = unresolvedHealthChecks.filter(h => h.check_type === 'api_health').length;

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Health Checks</h1>
          <p className="text-gray-600 mt-1">Monitor API downtime, parser errors, and system failures</p>
        </div>
        <Button onClick={refetch} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-600 mb-1">Total Checks</p>
          <p className="text-2xl font-bold text-gray-900">{healthChecks?.length || 0}</p>
        </Card>
        <Card className="p-4 border-2 border-red-200 bg-red-50">
          <p className="text-sm text-gray-600 mb-1">Unresolved Issues</p>
          <p className="text-2xl font-bold text-red-600">{unresolvedHealthChecks.length}</p>
        </Card>
        <Card className="p-4 border-2 border-red-300 bg-red-100">
          <p className="text-sm text-gray-600 mb-1">Critical Severity</p>
          <p className="text-2xl font-bold text-red-700">{criticalCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-600 mb-1">API Health Issues</p>
          <p className="text-2xl font-bold text-orange-600">{apiHealthCount}</p>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="p-6 bg-red-50 border-red-200">
          <p className="text-red-800">{error.message}</p>
        </Card>
      )}

      {/* Health Checks List */}
      {loading && !healthChecks ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : healthChecks && healthChecks.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-gray-500">No health checks found</p>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Unresolved Health Checks */}
          {unresolvedHealthChecks.length > 0 && (
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-3 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                Unresolved ({unresolvedHealthChecks.length})
              </h2>
              <div className="space-y-4">
                {unresolvedHealthChecks.map((healthCheck) => (
                  <HealthStatusCard
                    key={healthCheck.id}
                    healthCheck={healthCheck}
                    onResolve={updatingHealthId === healthCheck.id ? undefined : handleResolve}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Resolved Health Checks */}
          {resolvedHealthChecks.length > 0 && (
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-3 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Resolved ({resolvedHealthChecks.length})
              </h2>
              <div className="space-y-4">
                {resolvedHealthChecks.map((healthCheck) => (
                  <HealthStatusCard
                    key={healthCheck.id}
                    healthCheck={healthCheck}
                    onResolve={updatingHealthId === healthCheck.id ? undefined : handleResolve}
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
