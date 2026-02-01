"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Activity, CheckCircle, XCircle, Clock, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatsCard } from "@/components/stats-card";
import { RunTable } from "@/components/run-table";
import { ComplianceAlert } from "@/components/compliance-alert";
import { getRun } from "@/lib/api";
import { getStoredRunIds } from "@/lib/runs-store";
import type { Run } from "@/lib/types";

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    const runIds = getStoredRunIds();
    if (runIds.length === 0) {
      setRuns([]);
      setLoading(false);
      return;
    }

    try {
      const runPromises = runIds.slice(0, 10).map(async (id) => {
        try {
          return await getRun(id);
        } catch {
          return null;
        }
      });

      const results = await Promise.all(runPromises);
      const validRuns = results.filter((r): r is Run => r !== null);
      setRuns(validRuns);
    } catch (error) {
      console.error("Failed to fetch runs:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const stats = {
    active: runs.filter((r) => r.status === "running" || r.status === "grading").length,
    passed: runs.filter((r) => r.status === "completed").length,
    failed: runs.filter((r) => r.status === "failed").length,
    pending: runs.filter((r) => r.status === "pending").length,
  };

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Monitor your healthcare AI testing runs
          </p>
        </div>
        <Button asChild>
          <Link href="/new">
            <Plus className="mr-2 h-4 w-4" />
            New Test
          </Link>
        </Button>
      </header>

      {/* Content */}
      <div className="px-8 py-6 space-y-6">
        {/* Compliance Alert */}
        <ComplianceAlert />

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            label="Active Runs"
            value={stats.active}
            icon={Activity}
            iconClassName="bg-blue-100 dark:bg-blue-900"
          />
          <StatsCard
            label="Passed"
            value={stats.passed}
            icon={CheckCircle}
            iconClassName="bg-green-100 dark:bg-green-900"
          />
          <StatsCard
            label="Failed"
            value={stats.failed}
            icon={XCircle}
            iconClassName="bg-red-100 dark:bg-red-900"
          />
          <StatsCard
            label="Pending"
            value={stats.pending}
            icon={Clock}
            iconClassName="bg-gray-100 dark:bg-gray-800"
          />
        </div>

        {/* Recent Runs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse flex gap-4">
                    <div className="h-4 bg-muted rounded w-24" />
                    <div className="h-4 bg-muted rounded w-16" />
                    <div className="h-4 bg-muted rounded w-20" />
                    <div className="h-4 bg-muted rounded flex-1" />
                  </div>
                ))}
              </div>
            ) : (
              <RunTable runs={runs} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
