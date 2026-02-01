"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Plus, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunTable } from "@/components/run-table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listRuns } from "@/lib/api";
import type { Run, RunStatus } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<RunStatus | "all">("all");

  const fetchRuns = useCallback(async () => {
    try {
      const response = await listRuns();
      setRuns(response.runs);
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

  const filteredRuns =
    statusFilter === "all"
      ? runs
      : runs.filter((run) => run.status === statusFilter);

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Test Runs</h1>
          <p className="text-sm text-muted-foreground">
            View and manage all adversarial test runs
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
        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Filter by status:</span>
          </div>
          <Select
            value={statusFilter}
            onValueChange={(value) => setStatusFilter(value as RunStatus | "all")}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="grading">Grading</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="canceled">Canceled</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-sm text-muted-foreground">
            {filteredRuns.length} run{filteredRuns.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Runs Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">All Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="animate-pulse flex gap-4">
                    <div className="h-4 bg-muted rounded w-24" />
                    <div className="h-4 bg-muted rounded w-16" />
                    <div className="h-4 bg-muted rounded w-20" />
                    <div className="h-4 bg-muted rounded flex-1" />
                  </div>
                ))}
              </div>
            ) : (
              <RunTable runs={filteredRuns} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
