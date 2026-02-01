"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, X, ArrowRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getComplianceStatus, type GetComplianceStatusResponse } from "@/lib/api";

interface ComplianceAlertProps {
  onDismiss?: () => void;
}

export function ComplianceAlert({ onDismiss }: ComplianceAlertProps) {
  const [status, setStatus] = useState<GetComplianceStatusResponse | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getComplianceStatus();
        setStatus(data);
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();

    // Poll every 10 seconds
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  // Don't show if loading, dismissed, or status is valid
  if (loading || dismissed || !status || status.status === "valid") {
    return null;
  }

  return (
    <div className="mb-6 animate-in slide-in-from-top-2 duration-300">
      <div className="relative overflow-hidden rounded-lg border border-yellow-200 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-950/30 dark:to-orange-950/30 dark:border-yellow-800">
        {/* Animated background pulse */}
        <div className="absolute inset-0 bg-gradient-to-r from-yellow-400/10 to-orange-400/10 animate-pulse" />

        <div className="relative p-4">
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div className="flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900">
                <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">
                Compliance Testing Required
              </h3>
              <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                {status.reason || "A healthcare guideline has been updated. Your AI agent needs to be re-tested to maintain compliance certification."}
              </p>

              {/* Actions */}
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <Button
                  asChild
                  size="sm"
                  className="bg-yellow-600 hover:bg-yellow-700 text-white"
                >
                  <Link href="/new">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Start Testing Now
                  </Link>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-yellow-700 hover:text-yellow-800 hover:bg-yellow-100 dark:text-yellow-300 dark:hover:bg-yellow-900"
                >
                  <Link href="/compliance">
                    View Details
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>

            {/* Dismiss button */}
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 text-yellow-500 hover:text-yellow-700 dark:text-yellow-400 dark:hover:text-yellow-200"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Dismiss</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
