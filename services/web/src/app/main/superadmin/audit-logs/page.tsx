"use client";

import { useSuperadminAuditLogs } from "@/hooks/useApi";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, Search, Filter, X } from "lucide-react";
import { useState, useMemo } from "react";

export default function AuditLogsPage() {
  const [actionTypeFilter, setActionTypeFilter] = useState<string>("all");
  const [targetTypeFilter, setTargetTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [limit, setLimit] = useState(100);

  const { auditLogs, loading, error, refetch } = useSuperadminAuditLogs({
    limit,
    action_type: actionTypeFilter !== "all" ? actionTypeFilter : undefined,
    target_type: targetTypeFilter !== "all" ? targetTypeFilter : undefined,
  });

  // Client-side search filter
  const filteredLogs = useMemo(() => {
    if (!auditLogs) return [];
    if (!searchQuery) return auditLogs;

    const query = searchQuery.toLowerCase();
    return auditLogs.filter(log =>
      log.action_description.toLowerCase().includes(query) ||
      log.admin_username?.toLowerCase().includes(query) ||
      log.target_identifier?.toLowerCase().includes(query)
    );
  }, [auditLogs, searchQuery]);

  const clearFilters = () => {
    setActionTypeFilter("all");
    setTargetTypeFilter("all");
    setSearchQuery("");
  };

  const hasActiveFilters = actionTypeFilter !== "all" || targetTypeFilter !== "all" || searchQuery !== "";

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
          <p className="text-gray-600 mt-1">Track all admin actions and system events</p>
        </div>
        <Button onClick={refetch} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">Filters</h2>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="ml-auto"
              >
                <X className="h-4 w-4 mr-1" />
                Clear All
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Action Type Filter */}
            <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Action Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="classify_alert">Classify Alert</SelectItem>
                <SelectItem value="dismiss_alert">Dismiss Alert</SelectItem>
                <SelectItem value="escalate_alert">Escalate Alert</SelectItem>
                <SelectItem value="blacklist_user">Blacklist User</SelectItem>
                <SelectItem value="whitelist_user">Whitelist User</SelectItem>
                <SelectItem value="flag_user">Flag User</SelectItem>
                <SelectItem value="unflag_user">Unflag User</SelectItem>
                <SelectItem value="update_system_alert">Update System Alert</SelectItem>
              </SelectContent>
            </Select>

            {/* Target Type Filter */}
            <Select value={targetTypeFilter} onValueChange={setTargetTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Target Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Targets</SelectItem>
                <SelectItem value="alert">Alert</SelectItem>
                <SelectItem value="user">User</SelectItem>
                <SelectItem value="transaction">Transaction</SelectItem>
                <SelectItem value="system_alert">System Alert</SelectItem>
                <SelectItem value="health_check">Health Check</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between text-sm text-gray-600">
            <div>
              Showing <span className="font-semibold text-gray-900">{filteredLogs.length}</span> of{' '}
              <span className="font-semibold text-gray-900">{auditLogs?.length || 0}</span> logs
            </div>
            <Select value={limit.toString()} onValueChange={(v) => setLimit(Number(v))}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="50">50 logs</SelectItem>
                <SelectItem value="100">100 logs</SelectItem>
                <SelectItem value="200">200 logs</SelectItem>
                <SelectItem value="500">500 logs</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="p-6 bg-red-50 border-red-200">
          <p className="text-red-800">{error.message}</p>
        </Card>
      )}

      {/* Audit Logs Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Admin</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>IP Address</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !auditLogs ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                </TableCell>
              </TableRow>
            ) : filteredLogs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-gray-500">
                  No audit logs found
                </TableCell>
              </TableRow>
            ) : (
              filteredLogs.map((log) => (
                <TableRow key={log.id} className="hover:bg-gray-50">
                  <TableCell className="whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {new Date(log.created_at).toLocaleDateString()}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm font-medium text-gray-900">
                      {log.admin_username || 'System'}
                    </div>
                    <div className="text-xs text-gray-500">ID: {log.admin_id}</div>
                  </TableCell>
                  <TableCell>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                      {log.action_type.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-md">
                    <p className="text-sm text-gray-900 truncate">
                      {log.action_description}
                    </p>
                  </TableCell>
                  <TableCell>
                    {log.target_type && (
                      <div>
                        <div className="text-sm text-gray-900 capitalize">
                          {log.target_type}
                        </div>
                        {log.target_identifier && (
                          <div className="text-xs text-gray-500">
                            {log.target_identifier}
                          </div>
                        )}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.ip_address || '-'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Summary Stats */}
      {auditLogs && auditLogs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Total Actions</p>
            <p className="text-2xl font-bold text-gray-900">{auditLogs.length}</p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Unique Admins</p>
            <p className="text-2xl font-bold text-gray-900">
              {new Set(auditLogs.map(l => l.admin_id)).size}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Alert Actions</p>
            <p className="text-2xl font-bold text-gray-900">
              {auditLogs.filter(l => l.action_type.includes('alert')).length}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">User Actions</p>
            <p className="text-2xl font-bold text-gray-900">
              {auditLogs.filter(l => l.target_type === 'user').length}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
