"use client";

import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, Clock, XCircle } from "lucide-react";
import { useComplianceAlerts, useAlertActions } from "@/hooks/useApi";
import type { ComplianceAlert } from "@/lib/api";

export default function CompliancePage() {
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedAlert, setSelectedAlert] = useState<ComplianceAlert | null>(null);
  
  const apiFilters = useMemo(() => ({
    severity: severityFilter === 'all' ? undefined : severityFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit: 100,
    skip: 0
  }), [severityFilter, statusFilter]);
  
  const { alerts, total, loading, error, refetch } = useComplianceAlerts(apiFilters);
  const { updateComplianceAlert } = useAlertActions();
  
  const getSeverityBadge = (severity: string) => {
    const colors = {
      critical: "bg-red-100 text-red-700",
      high: "bg-orange-100 text-orange-700",
      medium: "bg-yellow-100 text-yellow-700",
      low: "bg-blue-100 text-blue-700",
    };
    return colors[severity.toLowerCase() as keyof typeof colors] || "bg-gray-100 text-gray-700";
  };
  
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'investigating':
        return <Clock className="h-4 w-4 text-blue-600" />;
      case 'dismissed':
        return <XCircle className="h-4 w-4 text-gray-600" />;
      case 'escalated':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
    }
  };
  
  const handleStatusChange = async (alertId: number, newStatus: string) => {
    try {
      await updateComplianceAlert(alertId, {
        status: newStatus as ComplianceAlert['status'],
        is_acknowledged: true,
      });
      refetch();
    } catch (error) {
      console.error('Failed to update alert:', error);
    }
  };
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  if (error) {
    return (
      <div className="p-8">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error loading alerts</h3>
          <p className="text-gray-600 mb-4">{error.message}</p>
          <button 
            onClick={refetch}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Page Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Compliance Alerts</h2>
        <p className="text-sm text-gray-500 mb-4">
          Monitor and manage compliance alerts ({total} total)
        </p>
        <div className="border-t border-gray-200" />
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-auto min-w-[140px] bg-white hover:bg-gray-50 border-black rounded-full h-9 px-4">
            <SelectValue placeholder="All Severities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-auto min-w-[140px] bg-white hover:bg-gray-50 border-black rounded-full h-9 px-4">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="investigating">Investigating</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="dismissed">Dismissed</SelectItem>
            <SelectItem value="escalated">Escalated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Alerts Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Alert ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>User</TableHead>
              <TableHead>RPS360 (0-1)</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    <span>Loading alerts...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : alerts && alerts.length > 0 ? (
              alerts.map((alert) => (
                <TableRow 
                  key={alert.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedAlert(alert)}
                >
                  <TableCell className="font-mono text-xs">{alert.id}</TableCell>
                  <TableCell className="capitalize text-xs">
                    {alert.alert_type.replace(/_/g, ' ')}
                  </TableCell>
                  <TableCell className="max-w-xs truncate">{alert.title}</TableCell>
                  <TableCell>
                    <Badge className={`${getSeverityBadge(alert.severity)} capitalize`}>
                      {alert.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(alert.status)}
                      <span className="capitalize text-sm">{alert.status}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {alert.user_name || `User ${alert.user_id}`}
                  </TableCell>
                  <TableCell>
                    <span className={`font-semibold ${
                      (alert.rps360 ?? 0) >= 0.7 ? 'text-red-600' :
                      (alert.rps360 ?? 0) >= 0.5 ? 'text-orange-600' :
                      'text-green-600'
                    }`}>
                      {alert.rps360 != null ? alert.rps360.toFixed(2) : 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-gray-600">
                    {formatDate(alert.created_at)}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={alert.status}
                      onValueChange={(value) => handleStatusChange(alert.id, value)}
                    >
                      <SelectTrigger className="w-auto h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="investigating">Investigating</SelectItem>
                        <SelectItem value="resolved">Resolved</SelectItem>
                        <SelectItem value="dismissed">Dismissed</SelectItem>
                        <SelectItem value="escalated">Escalated</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                  No alerts found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Alert Detail Modal/Sidebar could go here */}
      {selectedAlert && (
        <div 
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedAlert(null)}
        >
          <div 
            className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-semibold">{selectedAlert.title}</h3>
                <p className="text-sm text-gray-500">Alert ID: {selectedAlert.id}</p>
              </div>
              <button 
                onClick={() => setSelectedAlert(null)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Description</label>
                <p className="text-sm text-gray-900 mt-1">{selectedAlert.description}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">Type</label>
                  <p className="text-sm text-gray-900 capitalize">{selectedAlert.alert_type.replace(/_/g, ' ')}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Severity</label>
                  <Badge className={`${getSeverityBadge(selectedAlert.severity)} capitalize mt-1`}>
                    {selectedAlert.severity}
                  </Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Status</label>
                  <p className="text-sm text-gray-900 capitalize">{selectedAlert.status}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Priority</label>
                  <p className="text-sm text-gray-900 capitalize">{selectedAlert.priority}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">RPS360 Score (0-1)</label>
                  <p className="text-sm text-gray-900">{selectedAlert.rps360 !== undefined && selectedAlert.rps360 !== null ? selectedAlert.rps360.toFixed(2) : 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">User</label>
                  <p className="text-sm text-gray-900">{selectedAlert.user_name || `User ${selectedAlert.user_id}`}</p>
                </div>
              </div>
              
              {selectedAlert.alert_metadata && (
                <div>
                  <label className="text-sm font-medium text-gray-700">Metadata</label>
                  <pre className="text-xs bg-gray-100 p-3 rounded mt-1 overflow-x-auto">
                    {JSON.stringify(JSON.parse(selectedAlert.alert_metadata), null, 2)}
                  </pre>
                </div>
              )}
              
              <div className="pt-4 border-t">
                <p className="text-xs text-gray-500">
                  Created: {formatDate(selectedAlert.created_at)} | 
                  Updated: {formatDate(selectedAlert.updated_at)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
