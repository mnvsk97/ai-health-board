"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import {
  Layers,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  StopCircle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { listBatches } from "@/lib/api";
import type { BatchRun, BatchRunStatus } from "@/lib/types";

function getStatusIcon(status: BatchRunStatus) {
  switch (status) {
    case "pending":
      return <Clock className="h-4 w-4 text-muted-foreground" />;
    case "running":
      return <Play className="h-4 w-4 text-blue-500 animate-pulse" />;
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "canceled":
      return <StopCircle className="h-4 w-4 text-orange-500" />;
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
    <Badge variant={variants[status]}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

function BatchCard({ batch }: { batch: BatchRun }) {
  const progress =
    batch.total_scenarios > 0
      ? ((batch.completed_count + batch.failed_count + batch.canceled_count) /
          batch.total_scenarios) *
        100
      : 0;

  const timeAgo = batch.created_at
    ? formatDistanceToNow(new Date(batch.created_at * 1000), { addSuffix: true })
    : "Unknown";

  return (
    <Link href={`/batches/${batch.batch_id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getStatusIcon(batch.status)}
              <CardTitle className="text-base font-medium">
                {batch.batch_id}
              </CardTitle>
            </div>
            {getStatusBadge(batch.status)}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span>
                {batch.completed_count + batch.failed_count + batch.canceled_count} /{" "}
                {batch.total_scenarios}
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-2 text-center">
            <div>
              <div className="text-lg font-semibold">{batch.total_scenarios}</div>
              <div className="text-xs text-muted-foreground">Total</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-green-600">
                {batch.completed_count}
              </div>
              <div className="text-xs text-muted-foreground">Completed</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-red-600">
                {batch.failed_count}
              </div>
              <div className="text-xs text-muted-foreground">Failed</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-orange-600">
                {batch.canceled_count}
              </div>
              <div className="text-xs text-muted-foreground">Canceled</div>
            </div>
          </div>

          {/* Metadata */}
          <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t">
            <span>Agent: {batch.agent_type}</span>
            <span>Concurrency: {batch.concurrency}</span>
            <span>{timeAgo}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function BatchesPage() {
  const [batches, setBatches] = useState<BatchRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBatches = async () => {
    try {
      setLoading(true);
      const response = await listBatches(undefined, 50);
      setBatches(response.batches);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load batches");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchBatches, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Layers className="h-6 w-6" />
            Batch Runs
          </h1>
          <p className="text-sm text-muted-foreground">
            View and manage parallel test executions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchBatches}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button asChild>
            <Link href="/new">
              <Layers className="h-4 w-4 mr-2" />
              New Batch
            </Link>
          </Button>
        </div>
      </header>

      {/* Content */}
      <div className="px-8 py-6">
        {loading && batches.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-pulse text-muted-foreground">
              Loading batches...
            </div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <p className="text-destructive">{error}</p>
            <Button variant="outline" onClick={fetchBatches}>
              Try Again
            </Button>
          </div>
        ) : batches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <Layers className="h-12 w-12 text-muted-foreground/50" />
            <p className="text-muted-foreground">No batch runs yet</p>
            <Button asChild>
              <Link href="/new">Start a Batch Test</Link>
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {batches.map((batch) => (
              <BatchCard key={batch.batch_id} batch={batch} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
