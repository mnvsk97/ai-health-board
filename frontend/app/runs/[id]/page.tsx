"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Square, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusIndicator } from "@/components/status-indicator";
import { TranscriptViewer } from "@/components/transcript-viewer";
import { GradingResults } from "@/components/grading-results";
import { getRun, getTranscript, getReport, stopRun } from "@/lib/api";
import type { Run, TranscriptEntry, GradingResult } from "@/lib/types";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [grading, setGrading] = useState<GradingResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const runData = await getRun(runId);
      setRun(runData);

      const transcriptData = await getTranscript(runId);
      setTranscript(transcriptData.transcript);

      if (runData.status === "completed" || runData.status === "failed") {
        try {
          const reportData = await getReport(runId);
          setGrading(reportData.grading);
        } catch {
          // Report may not be available yet
        }
      }

      setError(null);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run data");
      setLoading(false);
    }
  }, [runId]);

  const handleStop = useCallback(async () => {
    setStopping(true);
    try {
      await stopRun(runId);
      await fetchData();
    } catch (err) {
      console.error("Failed to stop run:", err);
    } finally {
      setStopping(false);
    }
  }, [runId, fetchData]);

  useEffect(() => {
    fetchData();

    // Poll for updates while run is active
    intervalRef.current = setInterval(() => {
      fetchData();
    }, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData]);

  // Stop polling when run is complete
  useEffect(() => {
    const status = run?.status;
    if (status === "completed" || status === "failed" || status === "canceled") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [run]);

  if (loading) {
    return (
      <div className="flex flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-4 border-b bg-background px-8 py-6">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="animate-pulse">
            <div className="h-6 bg-muted rounded w-48" />
            <div className="h-4 bg-muted rounded w-32 mt-2" />
          </div>
        </header>
        <div className="px-8 py-6">
          <div className="animate-pulse space-y-4">
            <div className="h-32 bg-muted rounded-lg" />
            <div className="h-96 bg-muted rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-4 border-b bg-background px-8 py-6">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold tracking-tight">Run Details</h1>
        </header>
        <div className="px-8 py-6">
          <Card className="border-destructive">
            <CardContent className="py-6">
              <p className="text-destructive">{error || "Run not found"}</p>
              <p className="text-sm text-muted-foreground mt-2">
                Make sure the backend is running at http://localhost:8000
              </p>
              <Button variant="outline" className="mt-4" onClick={fetchData}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const isActive = run.status === "running" || run.status === "grading";

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{run.run_id}</h1>
              <StatusIndicator status={run.status} showProgress progress={75} />
            </div>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <Badge variant="secondary">{run.mode.replace(/_/g, " ")}</Badge>
              <span>{run.scenario_ids.length} scenario(s)</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {run.room_url && (
            <Button variant="outline" size="sm" asChild>
              <a href={run.room_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                Join Room
              </a>
            </Button>
          )}
          {isActive && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStop}
              disabled={stopping}
            >
              <Square className="mr-2 h-4 w-4" />
              {stopping ? "Stopping..." : "Stop"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </header>

      {/* Content */}
      <div className="px-8 py-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Transcript */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                Live Transcript
                {isActive && (
                  <span className="text-xs font-normal text-muted-foreground animate-pulse">
                    Updating...
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TranscriptViewer transcript={transcript} autoScroll={isActive} />
            </CardContent>
          </Card>

          {/* Grading Results */}
          <div className="lg:col-span-1">
            {grading ? (
              <GradingResults grading={grading} />
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Grading Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                    {isActive ? (
                      <>
                        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                        <p>Test in progress...</p>
                        <p className="text-sm">Results will appear when complete</p>
                      </>
                    ) : (
                      <p>No grading results available</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
