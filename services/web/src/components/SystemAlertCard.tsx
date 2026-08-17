import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./StatusBadge";
import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { SystemAlert } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SystemAlertCardProps {
  alert: SystemAlert;
  onAcknowledge?: (alertId: number) => void;
  onResolve?: (alertId: number) => void;
  className?: string;
}

export function SystemAlertCard({
  alert,
  onAcknowledge,
  onResolve,
  className
}: SystemAlertCardProps) {
  const severityIcons = {
    warning: AlertTriangle,
    error: XCircle,
    critical: AlertTriangle,
  };

  const severityColors = {
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
    critical: 'border-red-300 bg-red-100',
  };

  const Icon = severityIcons[alert.severity];

  return (
    <Card className={cn(
      "p-4 border-l-4",
      severityColors[alert.severity],
      className
    )}>
      <div className="flex items-start gap-4">
        <div className={cn(
          "p-2 rounded-lg",
          alert.severity === 'warning' && "bg-yellow-200 text-yellow-700",
          alert.severity === 'error' && "bg-red-200 text-red-700",
          alert.severity === 'critical' && "bg-red-300 text-red-800"
        )}>
          <Icon className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4 mb-2">
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">{alert.title}</h3>
              <p className="text-sm text-gray-600">{alert.description}</p>
            </div>
            <StatusBadge status={alert.status} />
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
            {alert.component && (
              <div>
                <span className="text-gray-500">Component:</span>{' '}
                <span className="font-medium text-gray-900">{alert.component}</span>
              </div>
            )}
            {alert.threshold_value && (
              <div>
                <span className="text-gray-500">Threshold:</span>{' '}
                <span className="font-medium text-gray-900">{alert.threshold_value}</span>
              </div>
            )}
            {alert.actual_value && (
              <div>
                <span className="text-gray-500">Actual:</span>{' '}
                <span className="font-medium text-gray-900">{alert.actual_value}</span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Triggered:</span>{' '}
              <span className="font-medium text-gray-900">
                {new Date(alert.triggered_at).toLocaleString()}
              </span>
            </div>
          </div>

          {alert.acknowledged_by && alert.status === 'acknowledged' && (
            <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                Acknowledged by <span className="font-medium">{alert.acknowledged_by}</span> at{' '}
                {new Date(alert.acknowledged_at!).toLocaleString()}
              </p>
            </div>
          )}

          {alert.status === 'resolved' && alert.resolution_notes && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">
                <span className="font-medium">Resolution:</span> {alert.resolution_notes}
              </p>
              {alert.resolved_at && (
                <p className="text-xs text-green-700 mt-1">
                  Resolved at {new Date(alert.resolved_at).toLocaleString()}
                </p>
              )}
            </div>
          )}

          {(alert.status === 'active' || alert.status === 'acknowledged') && (onAcknowledge || onResolve) && (
            <div className="flex gap-2 mt-4">
              {alert.status === 'active' && onAcknowledge && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onAcknowledge(alert.id)}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Acknowledge
                </Button>
              )}
              {onResolve && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => onResolve(alert.id)}
                  className="bg-black hover:bg-white border border-black hover:text-black"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark as Resolved
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
