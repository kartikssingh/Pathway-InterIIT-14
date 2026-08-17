"use client";

import { useMetricsSummary, useAlertResolutions, useAdminActivity } from "@/hooks/useApi";
import { MetricCard } from "@/components/MetricCard";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Activity,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Users,
  CheckCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function MetricsPage() {
  const [days, setDays] = useState(30);
  const { metrics, loading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useMetricsSummary(days);
  const { resolutions, loading: resolutionsLoading, refetch: refetchResolutions } = useAlertResolutions(days);
  const { activity, loading: activityLoading, refetch: refetchActivity } = useAdminActivity(days);

  const loading = metricsLoading || resolutionsLoading || activityLoading;

  const refetchAll = async () => {
    await Promise.all([
      refetchMetrics(),
      refetchResolutions(),
      refetchActivity(),
    ]);
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Metrics & Analytics</h1>
          <p className="text-gray-600 mt-1">Performance insights and trends</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>Period:</span>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <Button onClick={() => refetchAll()} variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error State */}
      {metricsError && (
        <Card className="p-6 bg-red-50 border-red-200">
          <p className="text-red-800">{metricsError.message}</p>
        </Card>
      )}

      {/* Key Performance Metrics */}
      {metrics && (
        <>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Key Performance Indicators</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Resolution Rate"
                value={metrics.resolution_rate.toFixed(1)}
                unit="%"
                icon={TrendingUp}
                severity={metrics.resolution_rate >= 70 ? 'success' : metrics.resolution_rate >= 50 ? 'warning' : 'error'}
              />
              <MetricCard
                title="API Error Rate"
                value={metrics.api_error_rate.toFixed(1)}
                unit="%"
                icon={TrendingDown}
                severity={metrics.api_error_rate <= 1 ? 'success' : metrics.api_error_rate <= 5 ? 'warning' : 'error'}
              />
              <MetricCard
                title="Avg Response Time"
                value={metrics.avg_response_time_ms < 1000 
                  ? metrics.avg_response_time_ms.toFixed(0) 
                  : (metrics.avg_response_time_ms / 1000).toFixed(1)}
                unit={metrics.avg_response_time_ms < 1000 ? "ms" : "sec"}
                icon={Clock}
                severity={metrics.avg_response_time_ms <= 1000 ? 'success' : metrics.avg_response_time_ms <= 5000 ? 'warning' : 'error'}
              />
            </div>
          </div>

          {/* Alert Statistics */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Alert Statistics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-6">
                <div className="flex items-center gap-3">
                  <Activity className="h-8 w-8 text-blue-600" />
                  <div>
                    <p className="text-sm text-gray-600">Total Alerts</p>
                    <p className="text-2xl font-bold text-gray-900">{metrics.total_alerts}</p>
                  </div>
                </div>
              </Card>
              <Card className="p-6">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm text-gray-600">Resolved</p>
                    <p className="text-2xl font-bold text-green-600">{metrics.resolved}</p>
                  </div>
                </div>
              </Card>
              <Card className="p-6">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-yellow-600" />
                  <div>
                    <p className="text-sm text-gray-600">Unresolved</p>
                    <p className="text-2xl font-bold text-yellow-600">{metrics.unresolved}</p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}

      {/* Alert Resolutions */}
      {resolutions && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Alert Resolution Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <Card className="p-4">
              <p className="text-sm text-gray-600 mb-1">Total</p>
              <p className="text-2xl font-bold text-gray-900">{resolutions.total_alerts}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-600 mb-1">Resolved</p>
              <p className="text-2xl font-bold text-green-600">{resolutions.resolved}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-600 mb-1">Unresolved</p>
              <p className="text-2xl font-bold text-yellow-600">{resolutions.unresolved}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-600 mb-1">Escalated</p>
              <p className="text-2xl font-bold text-orange-600">{resolutions.escalated}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-600 mb-1">Avg Resolution Time</p>
              <p className="text-2xl font-bold text-blue-600">{resolutions.avg_resolution_time_hours.toFixed(1)}h</p>
            </Card>
          </div>
        </div>
      )}

      {/* Admin Activity */}
      {activity && activity.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Admin Activity</h2>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Admin</TableHead>
                  <TableHead className="text-right">Total Actions</TableHead>
                  <TableHead className="text-right">Alerts Reviewed</TableHead>
                  <TableHead className="text-right">Users Flagged</TableHead>
                  <TableHead className="text-right">Decisions Made</TableHead>
                  <TableHead>Last Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activity.map((admin) => (
                  <TableRow key={admin.admin_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900">{admin.admin_username}</div>
                          <div className="text-xs text-gray-500">ID: {admin.admin_id}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-semibold">{admin.total_actions}</TableCell>
                    <TableCell className="text-right">{admin.alerts_reviewed}</TableCell>
                    <TableCell className="text-right">{admin.users_flagged}</TableCell>
                    <TableCell className="text-right">{admin.decisions_made}</TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {new Date(admin.last_active).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}
    </div>
  );
}
