"use client";

import { Badge } from "@/components/ui/badge";
import { CircleCheck, Ban, Shield, FileText, AlertTriangle, CreditCard, Edit3 } from "lucide-react";
import { getInitials } from "@/lib/utils";
import { useParams } from "next/navigation";
import { useUser, useUserActions } from "@/hooks/useApi";
import { useState } from "react";
import type { UserEvent } from "@/lib/transformers";

export default function UserDetailPage() {
  const params = useParams();
  const userId = parseInt(params.id as string);
  const { user, loading, error, refetch } = useUser(userId);
  const { suspendUser, updateUser, loading: actionLoading } = useUserActions();
  const [searchQuery, setSearchQuery] = useState("");
  
  // Filter events based on search query
  const filteredEvents = user?.events.filter(event => 
    event.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
    event.description?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];
  
  const handleSuspendUser = async () => {
    if (!user) return;
    try {
      await suspendUser(user.user_id);
      await refetch(); // Refresh user data
    } catch (error) {
      console.error('Failed to suspend user:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading user...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Error Loading User</h2>
          <p className="text-gray-500 mb-4">{error.message}</p>
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

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">User Not Found</h2>
          <p className="text-gray-500">The user you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main Content - Timeline */}
      <div className="flex-1 p-8 overflow-auto">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">{user.name}</h2>
          <p className="text-sm text-gray-500">Timeline View</p>
        </div>

        {/* Search Events */}
        <div className="mb-6">
          <div className="relative">
            <input
              type="text"
              placeholder="Search Events"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full max-w-md pl-10 pr-4 py-2 bg-white border border-black rounded-full h-9 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            />
            <svg
              className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Timeline Events */}
        <div className="space-y-4">
          {filteredEvents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {searchQuery ? 'No events match your search' : 'No events found'}
            </div>
          ) : (
            filteredEvents.map((event: UserEvent) => {
              const getEventIcon = (iconType: string, color: string) => {
                const iconColor = 
                  color === "blue" ? "text-blue-500" :
                  color === "red" ? "text-red-500" :
                  color === "green" ? "text-green-500" :
                  color === "yellow" ? "text-yellow-500" :
                  "text-gray-500";

                switch (iconType) {
                  case "edit":
                    return <Edit3 className={`h-5 w-5 ${iconColor}`} />;
                  case "alert":
                    return <AlertTriangle className={`h-5 w-5 ${iconColor}`} />;
                  case "transaction":
                    return <CreditCard className={`h-5 w-5 ${iconColor}`} />;
                  case "document":
                    return <FileText className={`h-5 w-5 ${iconColor}`} />;
                  default:
                    return <FileText className={`h-5 w-5 ${iconColor}`} />;
                }
              };

              return (
                <div key={event.id} className="flex gap-4">
                  {/* Timeline dot */}
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-3 h-3 rounded-full ${
                        event.color === "blue"
                          ? "bg-blue-500"
                          : event.color === "red"
                          ? "bg-red-500"
                          : event.color === "green"
                          ? "bg-green-500"
                          : event.color === "yellow"
                          ? "bg-yellow-500"
                          : "bg-gray-500"
                      }`}
                    />
                    {event.id < filteredEvents.length && (
                    <div className="w-0.5 h-full bg-gray-200 mt-2" />
                  )}
                </div>

                {/* Event Card */}
                <div
                  className={`flex-1 p-4 rounded-lg border mb-4 ${
                    event.isAlert
                      ? "bg-red-50 border-red-200"
                      : "bg-white border-gray-200"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {getEventIcon(event.iconType, event.color)}
                      </div>
                      <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">
                          {event.type}
                        </h3>
                        {event.isAlert && (
                          <Badge
                            variant="secondary"
                            className="bg-red-100 text-red-700 border-0 text-xs"
                          >
                            {event.ruleId}
                          </Badge>
                        )}
                      </div>
                      {event.by && (
                        <p className="text-sm text-gray-500">by {event.by}</p>
                      )}
                      {event.at && (
                        <p className="text-sm text-gray-500">at {event.at}</p>
                      )}
                      {event.document && (
                        <p className="text-sm text-gray-500">{event.document}</p>
                      )}
                      {event.description && (
                        <p className="text-sm text-gray-700 mt-2">
                          {event.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 whitespace-nowrap">
                    {event.timestamp}
                  </span>
                  </div>
                </div>
              </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Sidebar - User Info */}
      <aside className="w-80 border-l border-gray-200 p-6 overflow-auto bg-gray-50">
        {/* User Avatar */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white mb-4 flex items-center justify-center text-4xl font-bold">
            {getInitials(user.name)}
          </div>
          <Badge
            variant="secondary"
            className={`${
              user.accountStatus === "Active" 
                ? "bg-green-100 text-green-700" 
                : "bg-red-100 text-red-700"
            } border-0 flex items-center gap-1`}
          >
            {user.accountStatus === "Suspended" ? (
              <Ban className="h-3 w-3" />
            ) : (
              <CircleCheck className="h-3 w-3" />
            )}
            {user.accountStatus}
          </Badge>
        </div>

        {/* Risk Score */}
        <div className="mb-6 text-center">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Overall Risk Score
          </h3>
          <div className="relative inline-flex items-center justify-center w-32 h-32">
            <svg className="w-32 h-32 transform -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="#f3f4f6"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke={user.riskScore > 0.7 ? "#ef4444" : "#f59e0b"}
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${user.riskScore * 352} 352`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute text-center">
              <div className="text-3xl font-bold text-gray-900">
                {user.riskScore.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">{user.riskLevel} (0-1)</div>
            </div>
          </div>
        </div>

        {/* User Details */}
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-700">KYC Status</p>
            <div className="flex items-center gap-1 mt-1">
              <Shield 
                className={`h-4 w-4 ${
                  user.kycStatus === "Verified" 
                    ? "text-green-600" 
                    : user.kycStatus === "Pending"
                    ? "text-yellow-600"
                    : "text-red-600"
                }`} 
              />
              <p 
                className={`text-sm font-semibold ${
                  user.kycStatus === "Verified" 
                    ? "text-green-600" 
                    : user.kycStatus === "Pending"
                    ? "text-yellow-600"
                    : "text-red-600"
                }`}
              >
                {user.kycStatus}
              </p>
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700">Last login</p>
            <p className="text-sm text-gray-900">{user.lastLogin}</p>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700">Account Age</p>
            <p className="text-sm text-gray-900">{user.accountAge}</p>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700">Email</p>
            <p className="text-sm text-gray-900">{user.email}</p>
          </div>
        </div>

        {/* Suspend Account Button */}
        <button 
          onClick={handleSuspendUser}
          disabled={actionLoading || user.accountStatus === "Suspended"}
          className={`w-full mt-6 px-4 py-2 rounded-md flex items-center justify-center gap-2 ${
            user.accountStatus === "Suspended" 
              ? "bg-gray-400 text-white cursor-not-allowed" 
              : "bg-red-500 text-white hover:bg-red-600"
          }`}
        >
          <Ban className="h-4 w-4" />
          {actionLoading ? "Processing..." : 
           user.accountStatus === "Suspended" ? "Account Suspended" : "Suspend Account"}
        </button>
      </aside>
    </div>
  );
}
