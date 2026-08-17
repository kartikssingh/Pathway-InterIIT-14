"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getInitials } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Calendar, Info, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import { useUsers } from "@/hooks/useApi";

export default function UsersPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [kycStatusFilter, setKycStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  
  // Build API filters - memoize to prevent object recreation on every render
  const apiFilters = useMemo(() => ({
    q: searchQuery || undefined,
    kyc_status: kycStatusFilter !== "all" ? kycStatusFilter.toUpperCase() : undefined,
    riskCategory: riskFilter !== "all" ? riskFilter.toUpperCase() : undefined,
    blacklisted: statusFilter === "blacklisted" ? true : statusFilter === "active" ? false : undefined,
    limit: 50
  }), [searchQuery, kycStatusFilter, riskFilter, statusFilter]);
  
  const { users, loading, error, refetch } = useUsers(apiFilters);

  const handleRowClick = (userId: number) => {
    router.push(`/main/users/${userId}`);
  };
  
  if (error) {
    return (
      <div className="p-8">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error loading users</h3>
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
        <h2 className="text-2xl font-semibold text-gray-900">Users</h2>
        <p className="text-sm text-gray-500 mb-4">User Management</p>
        
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search User"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full max-w-md pl-11 pr-4 py-2 bg-[#FFFFFF] border border-black rounded-full h-9 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="blacklisted">Blacklisted</SelectItem>
          </SelectContent>
        </Select>

        <Select value={riskFilter} onValueChange={setRiskFilter}>
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="All Risk" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Risk</SelectItem>
            <SelectItem value="low">Low Risk</SelectItem>
            <SelectItem value="medium">Medium Risk</SelectItem>
            <SelectItem value="high">High Risk</SelectItem>
            <SelectItem value="critical">Critical Risk</SelectItem>
          </SelectContent>
        </Select>

        <Select value={kycStatusFilter} onValueChange={setKycStatusFilter}>
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="All KYC" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All KYC</SelectItem>
            <SelectItem value="verified">KYC Verified</SelectItem>
            <SelectItem value="pending">KYC Pending</SelectItem>
            <SelectItem value="rejected">KYC Rejected</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg overflow-hidden">
        <Table>
          <TableHeader className="[&_tr]:border-0">
            <TableRow className="bg-gray-50 border-0 rounded-lg">
              <TableHead className="font-semibold text-gray-900 first:rounded-l-lg">
                Name
              </TableHead>
              <TableHead className="font-semibold text-gray-900">
                Email
              </TableHead>
              <TableHead className="font-semibold text-gray-900">
                Created At
              </TableHead>
              <TableHead className="font-semibold text-gray-900">
                iNot Score (0-1)
              </TableHead>
              <TableHead className="font-semibold text-gray-900">
                Status
              </TableHead>
              <TableHead className="w-12 last:rounded-r-lg"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
                    <span className="ml-2">Loading users...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow
                  key={user.user_id}
                  className="hover:bg-gray-50 border-b border-gray-200 last:border-b-0 cursor-pointer"
                  onClick={() => handleRowClick(user.user_id)}
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center text-xs font-semibold">
                        {getInitials(user.name)}
                      </div>
                      <span className="font-medium">{user.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-gray-700">{user.email}</TableCell>
                  <TableCell className="text-gray-700">{user.createdAt}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-full max-w-[100px] h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            user.riskScore < 0.3
                              ? "bg-green-500"
                              : user.riskScore < 0.7
                              ? "bg-yellow-500"
                              : "bg-red-500"
                          }`}
                          style={{ width: `${Math.min(user.riskScore * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {user.riskScore.toFixed(2)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={`${user.statusColor} border-0 font-normal`}
                    >
                      {user.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="w-12">
                    <button className="text-gray-400 hover:text-gray-600 transition-colors">
                      <Info className="h-5 w-5" />
                    </button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
