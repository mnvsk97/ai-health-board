"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  ExternalLink,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  XCircle,
  Play,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  listGuidelines,
  getComplianceStatus,
  simulateGuidelineChange,
  type GetComplianceStatusResponse,
} from "@/lib/api";
import type { Guideline, Scenario } from "@/lib/types";

export default function CompliancePage() {
  const [guidelines, setGuidelines] = useState<Guideline[]>([]);
  const [complianceStatus, setComplianceStatus] = useState<GetComplianceStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [simulating, setSimulating] = useState<string | null>(null);
  const [showUpdateDialog, setShowUpdateDialog] = useState(false);
  const [newScenario, setNewScenario] = useState<Scenario | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [guidelinesRes, statusRes] = await Promise.all([
        listGuidelines().catch(() => ({ guidelines: [] })),
        getComplianceStatus().catch(() => null),
      ]);
      setGuidelines(guidelinesRes.guidelines);
      setComplianceStatus(statusRes);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSimulate = async (guidelineId: string) => {
    setSimulating(guidelineId);
    try {
      const result = await simulateGuidelineChange({ guideline_id: guidelineId });
      await fetchData();
      // Show the update dialog with the new scenario
      if (result.new_scenario) {
        setNewScenario(result.new_scenario);
        setShowUpdateDialog(true);
      }
    } catch (err) {
      console.error("Simulation failed:", err);
    } finally {
      setSimulating(null);
    }
  };

  const formatLastChecked = (timestamp: number | null) => {
    if (!timestamp) return "Never";
    const diff = Date.now() / 1000 - timestamp;
    const hours = Math.floor(diff / 3600);
    if (hours < 1) return "< 1 hour ago";
    if (hours < 24) return `${hours} hours ago`;
    const days = Math.floor(hours / 24);
    return `${days} day(s) ago`;
  };

  const getStatusIcon = () => {
    if (!complianceStatus) return <CheckCircle className="h-5 w-5 text-green-500" />;
    switch (complianceStatus.status) {
      case "valid":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "outdated":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "pending":
        return <Clock className="h-5 w-5 text-blue-500" />;
      default:
        return <XCircle className="h-5 w-5 text-red-500" />;
    }
  };

  const getStatusVariant = (): "pass" | "warning" | "secondary" => {
    if (!complianceStatus) return "pass";
    switch (complianceStatus.status) {
      case "valid":
        return "pass";
      case "outdated":
        return "warning";
      default:
        return "secondary";
    }
  };

  return (
    <div className="flex flex-col">
      {/* Guideline Update Dialog */}
      <Dialog open={showUpdateDialog} onOpenChange={setShowUpdateDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900">
                <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <DialogTitle className="text-xl">Guideline Updated</DialogTitle>
                <DialogDescription>
                  A healthcare guideline has changed
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="py-4 space-y-4">
            <div className="p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800">
              <p className="text-sm text-yellow-800 dark:text-yellow-200 font-medium mb-2">
                New Test Scenario Created
              </p>
              {newScenario && (
                <div className="space-y-2">
                  <p className="font-semibold">{newScenario.title}</p>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {newScenario.description}
                  </p>
                  <div className="flex gap-2 mt-2">
                    {newScenario.state && (
                      <Badge variant="secondary">{newScenario.state}</Badge>
                    )}
                    {newScenario.specialty && (
                      <Badge variant="outline">{newScenario.specialty}</Badge>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
              <p className="text-sm font-medium text-destructive mb-1">
                Action Required
              </p>
              <p className="text-sm text-muted-foreground">
                Your AI agent must be re-tested against the updated guidelines to maintain compliance certification.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setShowUpdateDialog(false)}
            >
              Later
            </Button>
            <Button asChild>
              <Link href="/new" onClick={() => setShowUpdateDialog(false)}>
                <Play className="mr-2 h-4 w-4" />
                Start Testing Now
              </Link>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Compliance</h1>
          <p className="text-sm text-muted-foreground">
            Monitor guideline compliance and certification status
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </header>

      {/* Content */}
      <div className="px-8 py-6 space-y-6">
        {/* Error State */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="py-4">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Compliance Status Panel */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                {getStatusIcon()}
                Compliance Status
              </CardTitle>
              <CardDescription>Current certification status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge variant={getStatusVariant()}>
                    {complianceStatus?.status?.toUpperCase() || "VALID"}
                  </Badge>
                </div>
                {complianceStatus?.reason && (
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-sm text-muted-foreground">{complianceStatus.reason}</p>
                  </div>
                )}
                {complianceStatus?.updated_at && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Last Updated</span>
                    <span>{new Date(complianceStatus.updated_at * 1000).toLocaleString()}</span>
                  </div>
                )}
                <div className="pt-4 border-t">
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="p-3 rounded-lg bg-green-500/10">
                      <div className="text-2xl font-bold text-green-600">{guidelines.length}</div>
                      <div className="text-xs text-muted-foreground">Guidelines</div>
                    </div>
                    <div className="p-3 rounded-lg bg-muted/50">
                      <div className="text-2xl font-bold">
                        {complianceStatus?.status === "valid" ? "100%" : "—"}
                      </div>
                      <div className="text-xs text-muted-foreground">Compliance</div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Guidelines Overview */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Monitored Guidelines
                  </CardTitle>
                  <CardDescription>
                    Healthcare guidelines used for scenario generation and compliance
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-muted rounded" />
                  ))}
                </div>
              ) : guidelines.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4" />
                  <p>No guidelines registered</p>
                  <p className="text-sm mt-1">
                    Run the guideline discovery script to add guidelines
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                        Guideline
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                        State
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                        Version
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-right">
                        Last Checked
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-right">
                        Actions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {guidelines.map((guideline) => (
                      <TableRow key={guideline.guideline_id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium font-mono text-sm">
                              {guideline.guideline_id}
                            </span>
                            {guideline.source_url && (
                              <a
                                href={guideline.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-foreground"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {guideline.state ? (
                            <Badge variant="secondary">{guideline.state}</Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {guideline.version || "—"}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          <div className="flex items-center justify-end gap-1">
                            <Clock className="h-3 w-3" />
                            <span className="text-sm">
                              {formatLastChecked(guideline.last_checked)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSimulate(guideline.guideline_id)}
                            disabled={simulating === guideline.guideline_id}
                          >
                            {simulating === guideline.guideline_id ? (
                              <RefreshCw className="h-3 w-3 animate-spin" />
                            ) : (
                              "Simulate Update"
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">About Compliance Monitoring</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <h4 className="font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  Guideline Tracking
                </h4>
                <p className="text-sm text-muted-foreground">
                  Guidelines are fetched from CDC, WHO, AHA, and other health organizations using
                  automated web scraping.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-primary" />
                  Change Detection
                </h4>
                <p className="text-sm text-muted-foreground">
                  When guidelines change, scenarios are automatically regenerated and agents are
                  flagged for recertification.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-primary" />
                  Certification
                </h4>
                <p className="text-sm text-muted-foreground">
                  Agents maintain valid certification by passing tests based on current guidelines.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
