"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { formatDistanceToNow, format } from "date-fns";
import {
  ArrowLeft,
  Layers,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  StopCircle,
  Square,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { getBatchRun, stopBatchRun, getRun } from "@/lib/api";
import type { BatchRun, BatchRunStatus, Run } from "@/lib/types";

function getStatusIcon(status: BatchRunStatus) {
  switch (status) {
    case "pending":
      return <Clock className="h-5 w-5 text-muted-foreground" />;
    case "running":
      return <Play className="h-5 w-5 text-blue-500 animate-pulse" />;
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-red-500" />;
    case "canceled":
      return <StopCircle className="h-5 w-5 text-orange-500" />;
    default:
      return null;
  }
}

function getStatusBadge(status: BatchRunStatus) {
  const variants: Record<BatchRunStatus, "default" | "secondary" | "destructive" | "outline"> = {
    pending: "secondary",
    running: "default",
    completed: "default",
    failed: "destructive",
    canceled: "outline",
  };
  return (
    <Badge variant={variants[status]} className="text-sm">
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-center">
          <div className={`text-3xl font-bold ${color || ""}`}>{value}</div>
          <div className="text-sm text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function BatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const batchId = params.id as string;

  const [batch, setBatch] = useState<BatchRun | null>(null);
  const [childRuns, setChildRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBatch = useCallback(async () => {
    try {
      const data = await getBatchRun(batchId);
      setBatch(data);

      // Fetch child run details if we have them
      if (data.child_run_ids.length > 0 && data.child_run_ids.length !== childRuns.length) {
        const runs = await Promise.all(
          data.child_run_ids.slice(0, 20).map((id) =>
            getRun(id).catch(() => null)
          )
        );
        setChildRuns(runs.filter((r): r is Run => r !== null));
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load batch");
    } finally {
      setLoading(false);
    }
  }, [batchId, childRuns.length]);

  useEffect(() => {
    fetchBatch();

    // Poll every 2 seconds while running
    const interval = setInterval(() => {
      if (batch?.status === "running" || batch?.status === "pending") {
        fetchBatch();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchBatch, batch?.status]);

  const handleStop = async () => {
    setStopping(true);
    try {
      await stopBatchRun(batchId);
      fetchBatch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop batch");
    } finally {
      setStopping(false);
    }
  };

  if (loading && !batch) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (error && !batch) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <p className="text-destructive">{error}</p>
        <Button variant="outline" onClick={() => router.push("/batches")}>
          Back to Batches
        </Button>
      </div>
    );
  }

  if (!batch) return null;

  const progress =
    batch.total_scenarios > 0
      ? ((batch.completed_count + batch.failed_count + batch.canceled_count) /
          batch.total_scenarios) *
        100
      : 0;

  const isRunning = batch.status === "running" || batch.status === "pending";
  const runningCount =
    batch.total_scenarios -
    batch.completed_count -
    batch.failed_count -
    batch.canceled_count;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b bg-background px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/batches">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div>
              <div className="flex items-center gap-3">
                {getStatusIcon(batch.status)}
                <h1 className="text-2xl font-semibold tracking-tight">
                  {batch.batch_id}
                </h1>
                {getStatusBadge(batch.status)}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {batch.agent_type} agent | {batch.concurrency} concurrent |{" "}
                {batch.turns} turns
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchBatch}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            {isRunning && (
              <Button
                variant="destructive"
                onClick={handleStop}
                disabled={stopping}
              >
                <Square className="h-4 w-4 mr-2" />
                {stopping ? "Stopping..." : "Stop All"}
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="px-8 py-6 space-y-6">
        {/* Progress Section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Progress</CardTitle>
            <CardDescription>
              {isRunning
                ? `${runningCount} scenarios in progress`
                : `Completed ${formatDistanceToNow(new Date((batch.completed_at || batch.created_at || 0) * 1000), { addSuffix: true })}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="font-medium">{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-3" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-4">
              <StatCard label="Total" value={batch.total_scenarios} />
              <StatCard
                label="Running"
                value={runningCount}
                color="text-blue-600"
              />
              <StatCard
                label="Completed"
                value={batch.completed_count}
                color="text-green-600"
              />
              <StatCard
                label="Failed"
                value={batch.failed_count}
                color="text-red-600"
              />
              <StatCard
                label="Canceled"
                value={batch.canceled_count}
                color="text-orange-600"
              />
            </div>
          </CardContent>
        </Card>

        {/* Timing Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Timing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Created</span>
                <p className="font-medium">
                  {batch.created_at
                    ? format(new Date(batch.created_at * 1000), "PPpp")
                    : "-"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Started</span>
                <p className="font-medium">
                  {batch.started_at
                    ? format(new Date(batch.started_at * 1000), "PPpp")
                    : "-"}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Completed</span>
                <p className="font-medium">
                  {batch.completed_at
                    ? format(new Date(batch.completed_at * 1000), "PPpp")
                    : "-"}
                </p>
              </div>
            </div>
            {batch.started_at && batch.completed_at && (
              <div className="mt-4 pt-4 border-t">
                <span className="text-muted-foreground text-sm">Duration: </span>
                <span className="font-medium">
                  {Math.round(batch.completed_at - batch.started_at)}s
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Child Runs */}
        {batch.child_run_ids.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                Child Runs ({batch.child_run_ids.length})
              </CardTitle>
              <CardDescription>
                Individual test runs spawned by this batch
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {childRuns.map((run) => (
                  <Link
                    key={run.run_id}
                    href={`/runs/${run.run_id}`}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {run.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : run.status === "failed" ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                      ) : run.status === "running" ? (
                        <Play className="h-4 w-4 text-blue-500 animate-pulse" />
                      ) : (
                        <Clock className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="font-mono text-sm">{run.run_id}</span>
                      <Badge variant="outline" className="text-xs">
                        {run.scenario_ids[0] || "unknown"}
                      </Badge>
                    </div>
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                  </Link>
                ))}
                {batch.child_run_ids.length > 20 && (
                  <p className="text-sm text-muted-foreground text-center pt-2">
                    Showing first 20 of {batch.child_run_ids.length} runs
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
