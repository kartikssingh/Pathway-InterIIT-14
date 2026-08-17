import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  severity?: 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

export function MetricCard({
  title,
  value,
  unit,
  icon: Icon,
  trend,
  severity = 'info',
  className
}: MetricCardProps) {
  const severityColors = {
    success: 'border-green-200 bg-green-50',
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
    info: 'border-blue-200 bg-blue-50',
  };

  const iconColors = {
    success: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
    info: 'text-blue-600',
  };

  return (
    <Card className={cn(
      "p-6 border-2",
      severityColors[severity],
      className
    )}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-2">{title}</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-gray-900">
              {value}
            </p>
            {unit && <span className="text-sm text-gray-500">{unit}</span>}
          </div>
          {trend && (
            <p className={cn(
              "text-sm mt-2 font-medium",
              trend.isPositive ? "text-green-600" : "text-red-600"
            )}>
              {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        {Icon && (
          <div className={cn(
            "p-3 rounded-lg",
            iconColors[severity]
          )}>
            <Icon className="h-6 w-6" />
          </div>
        )}
      </div>
    </Card>
  );
}
