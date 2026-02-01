"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  RefreshCw,
  Square,
  ExternalLink,
  Clock,
  Calendar,
  MessageSquare,
  FileText,
  PlayCircle,
  Download,
  FileJson,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusIndicator } from "@/components/status-indicator";
import { TranscriptViewer } from "@/components/transcript-viewer";
import { GradingResults } from "@/components/grading-results";
import { getRun, getTranscript, getReport, gradeRun, stopRun } from "@/lib/api";
import type { Run, TranscriptEntry, GradingResult } from "@/lib/types";

function formatTimestamp(ts: number | null): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function formatDuration(startTs: number | null, endTs: number | null): string {
  if (!startTs) return "—";
  const end = endTs || Date.now() / 1000;
  const seconds = Math.floor(end - startTs);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

function downloadFile(data: string, filename: string, mimeType: string) {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [grading, setGrading] = useState<GradingResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [grading_in_progress, setGradingInProgress] = useState(false);
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

  const handleGrade = useCallback(async () => {
    setGradingInProgress(true);
    try {
      const reportData = await gradeRun(runId);
      setGrading(reportData.grading);
    } catch (err) {
      console.error("Failed to grade run:", err);
    } finally {
      setGradingInProgress(false);
    }
  }, [runId]);

  const handleExportJson = useCallback(() => {
    const exportData = {
      run,
      transcript,
      grading,
      exportedAt: new Date().toISOString(),
    };
    downloadFile(
      JSON.stringify(exportData, null, 2),
      `run_${runId}_report.json`,
      "application/json"
    );
  }, [run, transcript, grading, runId]);

  const handleExportPdf = useCallback(() => {
    // Create a simple HTML report and open print dialog
    const passFail = grading?.pass_fail || "N/A";
    const severity = grading?.severity || "N/A";
    const finalScore = grading?.final_score?.toFixed(1) || "N/A";

    const transcriptHtml = transcript
      .map(
        (t) =>
          `<div style="margin-bottom: 8px; padding: 8px; background: ${
            t.role === "tester" ? "#f0f9ff" : t.role === "target" ? "#f0fdf4" : "#f5f5f5"
          }; border-radius: 4px;">
            <strong>${t.role.toUpperCase()}</strong>: ${t.content}
          </div>`
      )
      .join("");

    const evaluationsHtml =
      grading?.evaluations
        ?.map(
          (e) =>
            `<tr>
              <td style="padding: 8px; border: 1px solid #ddd;">${e.criterion}</td>
              <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${e.met ? "PASS" : "FAIL"}</td>
              <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${e.points_earned}/${e.points}</td>
              <td style="padding: 8px; border: 1px solid #ddd;">${e.reasoning}</td>
            </tr>`
        )
        .join("") || "";

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Test Run Report - ${runId}</title>
        <style>
          body { font-family: system-ui, -apple-system, sans-serif; margin: 40px; line-height: 1.6; }
          h1 { color: #1a1a1a; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }
          h2 { color: #333; margin-top: 30px; }
          .meta { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
          .meta-item { padding: 15px; background: #f5f5f5; border-radius: 8px; }
          .meta-label { font-size: 12px; color: #666; text-transform: uppercase; }
          .meta-value { font-size: 18px; font-weight: bold; margin-top: 5px; }
          .result { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; }
          .result.pass { background: #dcfce7; color: #166534; }
          .result.fail { background: #fee2e2; color: #991b1b; }
          .result.needs_review { background: #fef3c7; color: #92400e; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th { background: #f5f5f5; padding: 12px 8px; text-align: left; border: 1px solid #ddd; }
          @media print { body { margin: 20px; } }
        </style>
      </head>
      <body>
        <h1>Test Run Report</h1>
        <p><strong>Run ID:</strong> ${runId}</p>
        <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>

        <div class="meta">
          <div class="meta-item">
            <div class="meta-label">Status</div>
            <div class="meta-value">${run?.status?.toUpperCase()}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Mode</div>
            <div class="meta-value">${run?.mode?.replace(/_/g, " ")}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Started</div>
            <div class="meta-value">${formatTimestamp(run?.started_at || null)}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Messages</div>
            <div class="meta-value">${transcript.length}</div>
          </div>
        </div>

        ${
          grading
            ? `
        <h2>Grading Results</h2>
        <div class="meta">
          <div class="meta-item">
            <div class="meta-label">Result</div>
            <div class="meta-value"><span class="result ${passFail}">${passFail.toUpperCase()}</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Score</div>
            <div class="meta-value">${finalScore}%</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Severity</div>
            <div class="meta-value">${severity.toUpperCase()}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Break Type</div>
            <div class="meta-value">${grading.break_type?.replace(/_/g, " ") || "None"}</div>
          </div>
        </div>

        <h3>Criterion Evaluations</h3>
        <table>
          <thead>
            <tr>
              <th>Criterion</th>
              <th style="text-align: center;">Status</th>
              <th style="text-align: center;">Points</th>
              <th>Reasoning</th>
            </tr>
          </thead>
          <tbody>
            ${evaluationsHtml}
          </tbody>
        </table>
        `
            : "<p><em>No grading results available</em></p>"
        }

        <h2>Transcript</h2>
        ${transcriptHtml || "<p><em>No transcript available</em></p>"}
      </body>
      </html>
    `;

    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  }, [run, transcript, grading, runId]);

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
  const isCompleted = run.status === "completed" || run.status === "failed";
  const canGrade = isCompleted && !grading && transcript.length > 0;
  const canExport = transcript.length > 0;

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
              <h1 className="text-2xl font-semibold tracking-tight font-mono">{run.run_id}</h1>
              <StatusIndicator status={run.status} showProgress progress={isActive ? 75 : 100} />
            </div>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <Badge variant="secondary">{run.mode.replace(/_/g, " ")}</Badge>
              <span>{run.scenario_ids.length} scenario(s)</span>
              <span className="text-muted-foreground/50">|</span>
              <span>{transcript.length} messages</span>
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
          {canExport && (
            <>
              <Button variant="outline" size="sm" onClick={handleExportJson}>
                <FileJson className="mr-2 h-4 w-4" />
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportPdf}>
                <Download className="mr-2 h-4 w-4" />
                PDF
              </Button>
            </>
          )}
          {canGrade && (
            <Button
              variant="default"
              size="sm"
              onClick={handleGrade}
              disabled={grading_in_progress}
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              {grading_in_progress ? "Grading..." : "Grade Run"}
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
      <div className="px-8 py-6 space-y-6">
        {/* Run Metadata */}
        <Card>
          <CardContent className="py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Started</p>
                  <p className="text-sm font-medium">{formatTimestamp(run.started_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Duration</p>
                  <p className="text-sm font-medium">
                    {formatDuration(run.started_at, isActive ? null : run.updated_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Messages</p>
                  <p className="text-sm font-medium">{transcript.length}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Scenarios</p>
                  <p className="text-sm font-medium truncate max-w-[150px]" title={run.scenario_ids.join(", ")}>
                    {run.scenario_ids.length > 0 ? run.scenario_ids[0] : "None"}
                    {run.scenario_ids.length > 1 && ` +${run.scenario_ids.length - 1}`}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Tabs defaultValue="transcript" className="w-full">
          <TabsList>
            <TabsTrigger value="transcript" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Transcript
              {isActive && <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />}
            </TabsTrigger>
            <TabsTrigger value="grading" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Grading Results
              {grading && (
                <Badge
                  variant={grading.pass_fail === "pass" ? "pass" : grading.pass_fail === "needs_review" ? "warning" : "critical"}
                  className="ml-1 text-xs"
                >
                  {grading.pass_fail || grading.severity}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="transcript" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between">
                  Live Transcript
                  {isActive && (
                    <span className="text-xs font-normal text-muted-foreground animate-pulse">
                      Updating...
                    </span>
                  )}
                </CardTitle>
                <CardDescription>
                  Conversation between tester agent and target agent
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TranscriptViewer transcript={transcript} autoScroll={isActive} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="grading" className="mt-4">
            {grading_in_progress ? (
              <Card>
                <CardContent className="py-12">
                  <div className="flex flex-col items-center justify-center text-muted-foreground">
                    <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                    <p className="font-medium">Grading in Progress</p>
                    <p className="text-sm">Analyzing conversation with 6-stage pipeline...</p>
                  </div>
                </CardContent>
              </Card>
            ) : grading ? (
              <GradingResults grading={grading} />
            ) : (
              <Card>
                <CardContent className="py-12">
                  <div className="flex flex-col items-center justify-center text-muted-foreground">
                    {isActive ? (
                      <>
                        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                        <p className="font-medium">Test in Progress</p>
                        <p className="text-sm">Grading results will appear when complete</p>
                      </>
                    ) : canGrade ? (
                      <>
                        <FileText className="h-12 w-12 mb-4" />
                        <p className="font-medium">Ready to Grade</p>
                        <p className="text-sm mb-4">Click the button above to grade this run</p>
                        <Button onClick={handleGrade} disabled={grading_in_progress}>
                          <PlayCircle className="mr-2 h-4 w-4" />
                          Grade Run
                        </Button>
                      </>
                    ) : (
                      <>
                        <FileText className="h-12 w-12 mb-4" />
                        <p>No grading results available</p>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
