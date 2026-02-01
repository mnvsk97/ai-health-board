import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: number | string;
  icon?: LucideIcon;
  className?: string;
  iconClassName?: string;
}

export function StatsCard({
  label,
  value,
  icon: Icon,
  className,
  iconClassName,
}: StatsCardProps) {
  return (
    <Card className={cn("", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {label}
            </p>
            <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
          </div>
          {Icon && (
            <div
              className={cn(
                "flex h-12 w-12 items-center justify-center rounded-full bg-muted",
                iconClassName
              )}
            >
              <Icon className="h-6 w-6 text-muted-foreground" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
