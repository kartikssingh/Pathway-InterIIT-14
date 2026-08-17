import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const statusConfig: Record<string, { label: string; className: string }> = {
    healthy: {
      label: 'Healthy',
      className: 'bg-green-100 text-green-800 border-green-200'
    },
    degraded: {
      label: 'Degraded',
      className: 'bg-yellow-100 text-yellow-800 border-yellow-200'
    },
    failed: {
      label: 'Failed',
      className: 'bg-red-100 text-red-800 border-red-200'
    },
    recovering: {
      label: 'Recovering',
      className: 'bg-blue-100 text-blue-800 border-blue-200'
    },
    active: {
      label: 'Active',
      className: 'bg-orange-100 text-orange-800 border-orange-200'
    },
    acknowledged: {
      label: 'Acknowledged',
      className: 'bg-blue-100 text-blue-800 border-blue-200'
    },
    resolved: {
      label: 'Resolved',
      className: 'bg-green-100 text-green-800 border-green-200'
    },
    false_alarm: {
      label: 'False Alarm',
      className: 'bg-gray-100 text-gray-800 border-gray-200'
    },
    critical: {
      label: 'Critical',
      className: 'bg-red-100 text-red-800 border-red-200'
    },
    warning: {
      label: 'Warning',
      className: 'bg-yellow-100 text-yellow-800 border-yellow-200'
    },
    error: {
      label: 'Error',
      className: 'bg-red-100 text-red-800 border-red-200'
    },
    info: {
      label: 'Info',
      className: 'bg-blue-100 text-blue-800 border-blue-200'
    },
  };

  // Get config or fallback to default
  const config = statusConfig[status.toLowerCase()] || {
    label: status.charAt(0).toUpperCase() + status.slice(1).toLowerCase(),
    className: 'bg-gray-100 text-gray-800 border-gray-200'
  };

  return (
    <Badge 
      variant="outline" 
      className={cn(
        "font-medium",
        config.className,
        className
      )}
    >
      {config.label}
    </Badge>
  );
}
