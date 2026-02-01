"use client";

import { useState } from "react";
import { Shield, AlertTriangle, CheckCircle, RefreshCw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { simulateGuidelineChange } from "@/lib/api";
import type { ComplianceStatusType } from "@/lib/types";

interface CompliancePanelProps {
  className?: string;
}

const statusConfig: Record<
  ComplianceStatusType,
  { icon: typeof Shield; color: string; label: string; description: string }
> = {
  valid: {
    icon: CheckCircle,
    color: "text-pass",
    label: "Certified",
    description: "All guidelines are up to date",
  },
  outdated: {
    icon: AlertTriangle,
    color: "text-warning",
    label: "Outdated",
    description: "Some guidelines have been updated",
  },
  pending: {
    icon: RefreshCw,
    color: "text-muted-foreground",
    label: "Pending",
    description: "Compliance check in progress",
  },
};

export function CompliancePanel({ className }: CompliancePanelProps) {
  const [status, setStatus] = useState<ComplianceStatusType>("valid");
  const [isSimulating, setIsSimulating] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);

  const config = statusConfig[status];
  const Icon = config.icon;

  const handleSimulateChange = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      await simulateGuidelineChange({ guideline_id: "guideline_1" });
      setStatus("outdated");
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Failed to simulate change:", err);
      // Still update UI even if API fails
      setStatus("outdated");
      setLastUpdate(new Date());
    } finally {
      setIsSimulating(false);
    }
  };

  const handleRecertify = async () => {
    setIsSimulating(true);
    setStatus("pending");
    setError(null);
    try {
      // Simulate recertification process
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setStatus("valid");
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Failed to recertify:", err);
      setError("Recertification failed");
      setStatus("outdated");
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <CardTitle className="text-lg">Compliance Status</CardTitle>
          </div>
          <Badge
            variant={status === "valid" ? "pass" : status === "outdated" ? "warning" : "secondary"}
            className="gap-1"
          >
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </div>
        <CardDescription>{config.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Indicator */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
          <Icon className={cn("h-8 w-8", config.color)} />
          <div>
            <p className="font-medium">{config.label}</p>
            <p className="text-sm text-muted-foreground">
              Last checked: {lastUpdate.toLocaleTimeString()}
            </p>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/5">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Guideline Updates */}
        {status === "outdated" && (
          <div className="p-3 rounded-lg border border-warning/30 bg-warning/5">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-warning mt-0.5" />
              <div>
                <p className="text-sm font-medium">Guideline Update Detected</p>
                <p className="text-sm text-muted-foreground mt-1">
                  New CDC guidelines have been published. Your scenarios may need to be
                  re-evaluated to ensure compliance with the latest recommendations.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-2">
          {status === "outdated" && (
            <Button onClick={handleRecertify} disabled={isSimulating}>
              {isSimulating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Recertifying...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Recertify Now
                </>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            onClick={handleSimulateChange}
            disabled={isSimulating}
          >
            {isSimulating && status === "valid" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Simulating...
              </>
            ) : (
              "Simulate Guideline Change"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
