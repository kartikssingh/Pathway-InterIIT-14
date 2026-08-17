import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./StatusBadge";
import { AlertCircle, CheckCircle } from "lucide-react";
import { HealthCheck } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HealthStatusCardProps {
  healthCheck: HealthCheck;
  onResolve?: (healthId: number) => void;
  className?: string;
}

export function HealthStatusCard({
  healthCheck,
  onResolve,
  className
}: HealthStatusCardProps) {
  const severityColors = {
    info: 'border-blue-200 bg-blue-50',
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
    critical: 'border-red-300 bg-red-100',
  };

  return (
    <Card className={cn(
      "p-4 border-l-4",
      severityColors[healthCheck.severity],
      className
    )}>
      <div className="flex items-start gap-4">
        <div className={cn(
          "p-2 rounded-lg",
          healthCheck.severity === 'info' && "bg-blue-200 text-blue-700",
          healthCheck.severity === 'warning' && "bg-yellow-200 text-yellow-700",
          healthCheck.severity === 'error' && "bg-red-200 text-red-700",
          healthCheck.severity === 'critical' && "bg-red-300 text-red-800"
        )}>
          <AlertCircle className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4 mb-2">
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">
                {healthCheck.component_name}
              </h3>
              <p className="text-sm text-gray-600">
                {healthCheck.check_type.replace('_', ' ').toUpperCase()}
              </p>
            </div>
            <StatusBadge status={healthCheck.status} />
          </div>

          {healthCheck.error_message && (
            <div className="mt-2 p-3 bg-white bg-opacity-50 rounded-lg">
              <p className="text-sm text-gray-700">
                <span className="font-medium text-gray-900">{healthCheck.error_type}:</span>{' '}
                {healthCheck.error_message}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
            {healthCheck.response_time_ms && (
              <div>
                <span className="text-gray-500">Response Time:</span>{' '}
                <span className="font-medium text-gray-900">
                  {healthCheck.response_time_ms}ms
                </span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Retry Count:</span>{' '}
              <span className="font-medium text-gray-900">{healthCheck.retry_count}</span>
            </div>
            {healthCheck.user_impact && (
              <div>
                <span className="text-gray-500">User Impact:</span>{' '}
                <span className={cn(
                  "font-medium capitalize",
                  healthCheck.user_impact === 'high' && "text-red-600",
                  healthCheck.user_impact === 'medium' && "text-yellow-600",
                  healthCheck.user_impact === 'low' && "text-green-600"
                )}>
                  {healthCheck.user_impact}
                </span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Detected:</span>{' '}
              <span className="font-medium text-gray-900">
                {new Date(healthCheck.detected_at).toLocaleString()}
              </span>
            </div>
          </div>

          {healthCheck.affected_operations && healthCheck.affected_operations.length > 0 && (
            <div className="mt-3">
              <p className="text-sm text-gray-500 mb-1">Affected Operations:</p>
              <div className="flex flex-wrap gap-1">
                {healthCheck.affected_operations.map((op, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-white bg-opacity-75 rounded text-xs font-medium text-gray-700"
                  >
                    {op}
                  </span>
                ))}
              </div>
            </div>
          )}

          {healthCheck.is_resolved && healthCheck.resolution_notes && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">
                <span className="font-medium">Resolution:</span> {healthCheck.resolution_notes}
              </p>
            </div>
          )}

          {!healthCheck.is_resolved && onResolve && (
            <div className="flex gap-2 mt-4">
              <Button
                variant="default"
                size="sm"
                onClick={() => onResolve(healthCheck.id)}
                className="bg-black hover:bg-white border border-black hover:text-black"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Mark as Resolved
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
