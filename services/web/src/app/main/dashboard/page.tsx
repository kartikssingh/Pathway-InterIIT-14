"use client";

import { AlertTriangle, X } from "lucide-react";
import { useDashboard, useUnclassifiedAlerts, useAlertTrend, useAlertActions } from "@/hooks/useApi";
import { useEffect, useState, useMemo } from "react";
import { AlertClassificationCard } from "@/components/AlertClassificationCard";

export default function DashboardPage() {
  const { summary, riskDistribution, flaggedTransactions, loading, error, refetch } = useDashboard();
  
  // Get unclassified/pending alerts from dashboard endpoint
  const { alerts: unclassifiedAlerts, total: totalUnclassified, loading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useUnclassifiedAlerts({
    limit: 50,
    severity: 'all'
  });
  
  const { dismissAlert } = useAlertActions();
  const [dismissingAlert, setDismissingAlert] = useState<string | null>(null);
  // ❌ REMOVED: markAlert and markingAlert - classification no longer supported
  // const [markingAlert, setMarkingAlert] = useState<number | null>(null);
  
  // Show a console warning if alerts endpoint fails (but don't block the dashboard)
  useEffect(() => {
    if (alertsError) {
      console.warn('[Dashboard] Active alerts endpoint not available:', alertsError.message);
    }
  }, [alertsError]);
  
  // Sort all unclassified alerts by severity (critical > high > medium > low)
  const sortedAlerts = useMemo(() => {
    if (!unclassifiedAlerts) return [];
    
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    
    return [...unclassifiedAlerts].sort((a, b) => {
      const aSeverity = severityOrder[a.severity.toLowerCase() as keyof typeof severityOrder] ?? 4;
      const bSeverity = severityOrder[b.severity.toLowerCase() as keyof typeof severityOrder] ?? 4;
      return aSeverity - bSeverity;
    });
  }, [unclassifiedAlerts]);
  
  // Generate chart data from unclassified alerts grouped by week
  const chartData = useMemo(() => {
    if (!unclassifiedAlerts || unclassifiedAlerts.length === 0) {
      return null;
    }

    // Helper function to get week start date (Sunday)
    const getWeekStart = (date: Date) => {
      const d = new Date(date);
      const day = d.getDay();
      const diff = d.getDate() - day;
      const weekStart = new Date(d.setDate(diff));
      weekStart.setHours(0, 0, 0, 0);
      return weekStart;
    };

    // Helper function to format week range
    const formatWeekRange = (weekStart: Date) => {
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      return `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    };

    // Group alerts by week
    const alertsByWeek: { [key: string]: { weekStart: Date; count: number; critical: number; high: number; medium: number; low: number } } = {};
    
    unclassifiedAlerts.forEach(alert => {
      const date = new Date(alert.triggered_at);
      const weekStart = getWeekStart(date);
      const weekKey = weekStart.toISOString();
      
      if (!alertsByWeek[weekKey]) {
        alertsByWeek[weekKey] = { weekStart, count: 0, critical: 0, high: 0, medium: 0, low: 0 };
      }
      
      alertsByWeek[weekKey].count++;
      const severity = alert.severity.toLowerCase();
      if (severity === 'critical') alertsByWeek[weekKey].critical++;
      else if (severity === 'high') alertsByWeek[weekKey].high++;
      else if (severity === 'medium') alertsByWeek[weekKey].medium++;
      else if (severity === 'low') alertsByWeek[weekKey].low++;
    });

    // Convert to array and sort by week
    const sortedWeeks = Object.keys(alertsByWeek).sort((a, b) => 
      new Date(a).getTime() - new Date(b).getTime()
    );

    if (sortedWeeks.length === 0) return null;

    const points = sortedWeeks.map(weekKey => ({
      timestamp: formatWeekRange(alertsByWeek[weekKey].weekStart),
      count: alertsByWeek[weekKey].count,
      critical_count: alertsByWeek[weekKey].critical,
      high_count: alertsByWeek[weekKey].high,
      medium_count: alertsByWeek[weekKey].medium,
      low_count: alertsByWeek[weekKey].low,
    }));

    const maxCount = Math.max(...points.map(p => p.count), 1);
    const width = 400;
    const height = 150;
    const padding = 10;

    // Calculate positions
    const step = width / (points.length - 1 || 1);
    
    return points.map((point, index) => {
      const x = index * step;
      const y = height - padding - ((point.count / maxCount) * (height - padding * 2));
      return { x, y, count: point.count, timestamp: point.timestamp };
    });
  }, [unclassifiedAlerts]);
  
  // Debug logging
  useEffect(() => {
    console.log('Dashboard data:', { summary, riskDistribution, flaggedTransactions, loading, error });
    console.log('Total transactions from API:', summary?.total_transactions);
    console.log('Alert data:', { unclassifiedAlerts, totalUnclassified, sortedAlerts, chartData, alertsLoading, alertsError });
  }, [summary, riskDistribution, flaggedTransactions, loading, error, unclassifiedAlerts, totalUnclassified, sortedAlerts, chartData, alertsLoading, alertsError]);
  
  const handleDismissAlert = async (alertId: string) => {
    try {
      setDismissingAlert(alertId);
      await dismissAlert(alertId, {
        reason: "Reviewed by admin",
        notes: "Dismissed from dashboard"
      });
      // Refetch alerts after dismissal
      refetchAlerts();
    } catch (error) {
      console.error('Failed to dismiss alert:', error);
    } finally {
      setDismissingAlert(null);
    }
  };
  
  // ❌ REMOVED: handleMarkAlert - classification no longer supported
  // const handleMarkAlert = async (alertId: number, isPositive: boolean, notes: string) => { ... };
  
  // Show error if dashboard data fails to load
  if (error) {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-red-900 mb-2">Error loading dashboard</h3>
            <p className="text-red-700 mb-4">{error.message}</p>
            <div className="bg-white rounded p-3 mb-4 text-xs text-gray-700">
              <p className="font-medium mb-2">Troubleshooting:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Check if backend is running on http://localhost:8000</li>
                <li>Verify CORS settings allow requests from frontend</li>
                <li>Check browser console for detailed error messages</li>
                <li>Try: <code className="bg-gray-100 px-1 rounded">curl http://localhost:8000/dashboard/summary</code></li>
              </ul>
            </div>
            <button 
              onClick={refetch}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500">Bird Eye View</p>
        
        {/* Debug info - Remove in production
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
            <strong>Debug:</strong> Loading: {loading ? 'Yes' : 'No'} | 
            Summary: {summary ? 'Loaded' : 'Null'} | 
            Risk: {riskDistribution ? 'Loaded' : 'Null'} | 
            Flagged: {flaggedTransactions?.length || 0} items
          </div>
        )} */}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Section - Stats and Alerts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-3 gap-4">
            {loading ? (
              <>
                {[1, 2, 3].map(i => (
                  <div key={i} className="bg-white p-6 rounded-lg border border-gray-200 animate-pulse">
                    <div className="h-3 bg-gray-200 rounded mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2 mb-4"></div>
                    <div className="h-8 bg-gray-200 rounded mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                  </div>
                ))}
              </>
            ) : (
              <>
                <div className="bg-white p-6 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Total Users</div>
                  <div className="text-sm text-gray-400 mb-2">(All Time)</div>
                  <div className="text-3xl font-bold text-gray-900 mb-2">{summary?.total_users || 0}</div>
                </div>

                <div className="bg-white p-6 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Blacklisted Users</div>
                  <div className="text-sm text-gray-400 mb-2">(Current)</div>
                  <div className="text-3xl font-bold text-red-600 mb-2">{summary?.blacklisted_users || 0}</div>
                </div>

                <div className="bg-white p-6 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Total Transactions</div>
                  <div className="text-sm text-gray-400 mb-2">Volume: ₹{summary?.total_volume ? summary.total_volume.toLocaleString('en-IN') : '0'}</div>
                  <div className="text-3xl font-bold text-gray-900 mb-2">{summary?.total_transactions || 0}</div>
                  <div className="text-xs text-blue-600">
                    Avg RPS 360: {summary?.average_i360_score !== undefined && summary.average_i360_score !== null ? summary.average_i360_score.toFixed(2) : 'N/A'} (0-1 scale)
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Active Alerts - Sorted by Severity */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Active Alerts</h3>
                <p className="text-xs text-gray-500 mt-1">
                  {totalUnclassified} alerts pending review • Sorted by severity
                </p>
              </div>
              {alertsLoading && <span className="text-xs text-gray-500">Loading...</span>}
            </div>
            <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
              {alertsError ? (
                <div className="text-center py-8 px-4">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-full mb-3">
                    <AlertTriangle className="w-6 h-6 text-yellow-600" />
                  </div>
                  <p className="text-sm font-medium text-gray-900 mb-1">Failed to Load Alerts</p>
                  <p className="text-xs text-gray-500 mb-4">
                    {alertsError.message || 'Unable to fetch active alerts from the backend.'}
                  </p>
                  <button 
                    onClick={refetchAlerts}
                    className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Retry Connection
                  </button>
                </div>
              ) : alertsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="p-4 rounded-lg border border-gray-200 animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : sortedAlerts && sortedAlerts.length > 0 ? (
                sortedAlerts.map((alert) => (
                  <AlertClassificationCard
                    key={alert.id}
                    alert={alert}
                    onDismiss={handleDismissAlert}
                    isDismissing={dismissingAlert === alert.id}
                  />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>No active alerts</p>
                  <p className="text-xs mt-1">All alerts have been reviewed or resolved</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Section - Live Feed */}
        <div className="space-y-6">
          {/* Live Alert Feed - Active Alerts */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-gray-900">Active Alert Feed</h3>
                <p className="text-xs text-gray-500 mt-1">Recent alerts pending review</p>
              </div>
              {alertsLoading && <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse" title="Loading"></div>}
            </div>
            <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
              {alertsError ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
                  <p className="font-medium">Endpoint Not Available</p>
                  <p className="text-xs mt-1">Backend implementation pending</p>
                </div>
              ) : sortedAlerts && sortedAlerts.length > 0 ? (
                sortedAlerts.slice(0, 20).map((alert) => (
                  <div key={alert.id} className="flex items-center justify-between text-sm gap-2 p-2 hover:bg-gray-50 rounded transition-colors">
                    <span className="text-gray-500 font-mono text-xs">{new Date(alert.triggered_at).toLocaleTimeString()}</span>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${
                        alert.severity.toLowerCase() === 'critical' ? 'bg-red-100 text-red-700' :
                        alert.severity.toLowerCase() === 'high' ? 'bg-orange-100 text-orange-700' :
                        alert.severity.toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {alert.severity}
                    </span>
                    <span className="text-gray-700 font-medium text-xs">#{alert.alert_id}</span>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500 text-sm">
                  <p>No unclassified alerts</p>
                  <p className="text-xs mt-1">All alerts have been reviewed</p>
                </div>
              )}
            </div>
          </div>

          {/* Alert Trend - Active Alerts by Date */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-gray-900">
                  Active Alerts Trend
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  {totalUnclassified} active alerts • Grouped by week
                </p>
              </div>
              {alertsLoading && <span className="text-xs text-gray-500">Loading...</span>}
            </div>
            <div className="p-6">
              {alertsError ? (
                <div className="h-48 flex flex-col items-center justify-center text-gray-500">
                  <AlertTriangle className="w-10 h-10 text-yellow-500 mb-2" />
                  <p className="text-sm">Chart unavailable</p>
                  <p className="text-xs">Backend endpoint not implemented</p>
                </div>
              ) : alertsLoading ? (
                <div className="h-48 flex items-center justify-center">
                  <div className="h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : chartData && chartData.length > 0 ? (
                <div className="h-48 relative">
                  <svg className="w-full h-full" viewBox="0 0 400 150" preserveAspectRatio="none">
                    {/* Grid lines */}
                    <line x1="0" y1="150" x2="400" y2="150" stroke="#e5e7eb" strokeWidth="1" />
                    <line x1="0" y1="112.5" x2="400" y2="112.5" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="0" y1="75" x2="400" y2="75" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2,2" />
                    <line x1="0" y1="37.5" x2="400" y2="37.5" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2,2" />
                    
                    {/* Alert line - Critical + High */}
                    <path
                      d={`M ${chartData.map((p, i) => `${i === 0 ? '' : 'L '}${p.x},${p.y}`).join(' ')}`}
                      fill="none"
                      stroke="#ef4444"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    
                    {/* Data points */}
                    {chartData.map((point, index) => (
                      <g key={index}>
                        <circle 
                          cx={point.x} 
                          cy={point.y} 
                          r="4" 
                          fill="#ef4444"
                          className="hover:r-6 transition-all cursor-pointer"
                        />
                        <title>{`${new Date(point.timestamp).toLocaleTimeString()}: ${point.count} alerts`}</title>
                      </g>
                    ))}
                  </svg>
                  
                  {/* Legend */}
                  <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                    <span>
                      {chartData[0] && chartData[0].timestamp}
                    </span>
                    <span className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      Active Alerts
                    </span>
                    <span>
                      {chartData[chartData.length - 1] && chartData[chartData.length - 1].timestamp}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-gray-500 text-sm">
                  <p>No trend data available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
