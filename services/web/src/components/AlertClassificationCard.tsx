// Alert Display Component (Classification removed - no longer supported by backend)
'use client';

import { AlertTriangle, CheckCircle, XCircle, X } from 'lucide-react';
import { CriticalAlert } from '@/lib/api';

interface AlertCardProps {
  alert: CriticalAlert;
  // ❌ REMOVED: onMark - Alert classification is no longer supported
  // onMark: (alertId: number, isPositive: boolean, notes: string) => Promise<void>;
  onDismiss?: (alertId: string) => Promise<void>;
  // ❌ REMOVED: isMarking - No longer needed
  // isMarking?: boolean;
  isDismissing?: boolean;
}

export function AlertClassificationCard({ 
  alert, 
  onDismiss,
  isDismissing = false
}: AlertCardProps) {
  // ❌ REMOVED: Classification state - no longer needed
  // const [showNotesInput, setShowNotesInput] = useState(false);
  // const [notes, setNotes] = useState('');
  // const [pendingAction, setPendingAction] = useState<'positive' | 'negative' | null>(null);

  const getSeverityColor = (severity: string) => {
    const normalizedSeverity = severity.toLowerCase();
    switch (normalizedSeverity) {
      case 'critical':
        return 'border-red-500 bg-red-50';
      case 'high':
        return 'border-orange-500 bg-orange-50';
      case 'medium':
        return 'border-yellow-500 bg-yellow-50';
      case 'low':
        return 'border-blue-500 bg-blue-50';
      default:
        return 'border-gray-300 bg-gray-50';
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    const normalizedSeverity = severity.toLowerCase();
    switch (normalizedSeverity) {
      case 'critical':
        return 'bg-red-100 text-red-700';
      case 'high':
        return 'bg-orange-100 text-orange-700';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700';
      case 'low':
        return 'bg-blue-100 text-blue-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  // ❌ REMOVED: Classification handlers - no longer supported
  // const handleMarkPositive = () => { ... };
  // const handleMarkNegative = () => { ... };
  // const handleSubmitClassification = async () => { ... };
  // const handleCancel = () => { ... };

  const getStatusBadgeColor = (status?: string) => {
    if (!status) return 'bg-gray-100 text-gray-700';
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'active':
        return 'bg-blue-100 text-blue-700';
      case 'investigating':
        return 'bg-purple-100 text-purple-700';
      case 'resolved':
        return 'bg-green-100 text-green-700';
      case 'dismissed':
        return 'bg-gray-100 text-gray-700';
      case 'escalated':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const formatTimeAgo = (seconds: number) => {
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className={`rounded-lg border-l-4 p-4 ${getSeverityColor(alert.severity)}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0 text-gray-700" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-gray-500">#{alert.alert_id}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getSeverityBadgeColor(alert.severity)}`}>
                {alert.severity}
              </span>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700 capitalize">
                {alert.alert_type.replace(/_/g, ' ')}
              </span>
              {alert.status && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusBadgeColor(alert.status)}`}>
                  {alert.status.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            {alert.title && (
              <h3 className="font-semibold text-gray-900">
                {alert.title}
              </h3>
            )}
          </div>
        </div>
        {onDismiss && (
          <button
            onClick={() => onDismiss(String(alert.id))}
            disabled={isDismissing}
            className="ml-2 p-1 hover:bg-black/10 rounded-full transition-colors shrink-0"
            title="Dismiss alert"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Description */}
      {alert.description && (
        <p className="text-sm text-gray-700 mb-3 ml-8">{alert.description}</p>
      )}

      {/* Alert Details */}
      <div className="ml-8 mb-3 space-y-1 text-sm text-gray-600">
        {alert.user_name && (
          <div className="flex items-center gap-2">
            <span className="font-medium">User:</span>
            <span>{alert.user_name}</span>
            {alert.entity_id && <span className="text-xs">({alert.entity_id})</span>}
          </div>
        )}
        {alert.user_id && (
          <div className="flex items-center gap-2">
            <span className="font-medium">User ID:</span>
            <span>{alert.user_id}</span>
          </div>
        )}
        {alert.rps360 !== undefined && alert.rps360 !== null && (
          <div className="flex items-center gap-2">
            <span className="font-medium">RPS 360 (0-1):</span>
            <span className="font-mono">{alert.rps360.toFixed(2)}</span>
          </div>
        )}
        {alert.amount !== undefined && alert.amount !== null && (
          <div className="flex items-center gap-2">
            <span className="font-medium">Amount:</span>
            <span>₹{alert.amount.toLocaleString('en-IN')}</span>
          </div>
        )}
        {alert.transaction_id !== undefined && alert.transaction_id !== null && (
          <div className="flex items-center gap-2">
            <span className="font-medium">Transaction ID:</span>
            <span>{alert.transaction_id}</span>
          </div>
        )}
        {alert.triggered_at && (
          <div className="flex items-center gap-2">
            <span className="font-medium">Triggered:</span>
            {alert.time_ago_seconds !== undefined && (
              <span>{formatTimeAgo(alert.time_ago_seconds)} • </span>
            )}
            <span className="text-xs text-gray-500">
              {new Date(alert.triggered_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* ❌ REMOVED: Classification Actions - No longer supported by backend
      Alert status is now managed through the status field (active, investigating, resolved, dismissed, escalated)
      Use the status badge above to see the current alert state. */}
    </div>
  );
}

// ❌ REMOVED: ClassificationBadge - Alert classification is no longer supported
// Use StatusBadge component instead to show alert status
interface StatusBadgeProps {
  alert: CriticalAlert;
}

export function StatusBadge({ alert }: StatusBadgeProps) {
  const getStatusIcon = (status?: string) => {
    if (!status) return <AlertTriangle className="h-3 w-3" />;
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'active':
        return <AlertTriangle className="h-3 w-3" />;
      case 'investigating':
        return <AlertTriangle className="h-3 w-3" />;
      case 'resolved':
        return <CheckCircle className="h-3 w-3" />;
      case 'dismissed':
        return <XCircle className="h-3 w-3" />;
      case 'escalated':
        return <AlertTriangle className="h-3 w-3" />;
      default:
        return <AlertTriangle className="h-3 w-3" />;
    }
  };

  const getBadgeColor = (status?: string) => {
    if (!status) return 'bg-gray-100 text-gray-700 border-gray-200';
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'active':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'investigating':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'resolved':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'dismissed':
        return 'bg-gray-100 text-gray-700 border-gray-200';
      case 'escalated':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const status = alert.status || 'active';
  
  return (
    <span 
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getBadgeColor(status)}`}
      title={`Alert status: ${status}`}
    >
      {getStatusIcon(status)}
      {status.toUpperCase().replace(/_/g, ' ')}
    </span>
  );
}
