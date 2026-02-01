"use client";

import { cn } from "@/lib/utils";
import type { RunStatus } from "@/lib/types";

const statusConfig: Record<
  RunStatus,
  { color: string; label: string; animate?: boolean }
> = {
  pending: { color: "bg-muted-foreground/30", label: "Pending" },
  running: { color: "bg-blue-500", label: "Running", animate: true },
  grading: { color: "bg-orange-500", label: "Grading", animate: true },
  completed: { color: "bg-pass", label: "Completed" },
  failed: { color: "bg-fail", label: "Failed" },
  canceled: { color: "bg-muted-foreground", label: "Canceled" },
};

interface StatusIndicatorProps {
  status: RunStatus;
  progress?: number;
  showLabel?: boolean;
  showProgress?: boolean;
  size?: "sm" | "md";
}

export function StatusIndicator({
  status,
  progress,
  showLabel = true,
  showProgress = false,
  size = "md",
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const dotSize = size === "sm" ? "w-2 h-2" : "w-2.5 h-2.5";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "rounded-full",
          dotSize,
          config.color,
          config.animate && "animate-pulse"
        )}
      />
      {showLabel && (
        <span className={cn("font-medium", textSize)}>{config.label}</span>
      )}
      {showProgress && config.animate && progress !== undefined && (
        <div className="w-24 h-1 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
