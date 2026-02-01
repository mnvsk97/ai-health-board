"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  RefreshCw,
  CheckCircle,
  XCircle,
  Globe,
  Database,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listScenarios, updateScenario } from "@/lib/api";
import type { Scenario } from "@/lib/types";

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listScenarios();
      setScenarios(response.scenarios);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApprovalToggle = async (scenario: Scenario) => {
    setUpdating(scenario.scenario_id);
    try {
      const updated = await updateScenario(scenario.scenario_id, {
        clinician_approved: !scenario.clinician_approved,
      });
      setScenarios((prev) =>
        prev.map((s) => (s.scenario_id === updated.scenario_id ? updated : s))
      );
    } catch (err) {
      console.error("Failed to update scenario:", err);
    } finally {
      setUpdating(null);
    }
  };

  const approvedCount = scenarios.filter((s) => s.clinician_approved).length;
  const webCount = scenarios.filter((s) => s.source_type === "web").length;
  const benchCount = scenarios.filter((s) => s.source_type === "bench").length;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Scenarios</h1>
          <p className="text-sm text-muted-foreground">
            Manage test scenarios and approval status
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </header>

      {/* Content */}
      <div className="px-8 py-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{scenarios.length}</p>
                  <p className="text-xs text-muted-foreground">Total Scenarios</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{approvedCount}</p>
                  <p className="text-xs text-muted-foreground">Approved</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Globe className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{webCount}</p>
                  <p className="text-xs text-muted-foreground">From Web</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Database className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{benchCount}</p>
                  <p className="text-xs text-muted-foreground">From HealthBench</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error State */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="py-4">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Scenarios Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              All Scenarios
            </CardTitle>
            <CardDescription>
              Toggle approval status for each scenario
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-12 bg-muted rounded" />
                ))}
              </div>
            ) : scenarios.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4" />
                <p>No scenarios found</p>
                <p className="text-sm mt-1">
                  Run the scenario generation script to create scenarios
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Title
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Source
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      State
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Specialty
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Criteria
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-center">
                      Human Approved
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scenarios.map((scenario) => (
                    <TableRow key={scenario.scenario_id}>
                      <TableCell>
                        <div className="max-w-[300px]">
                          <p className="font-medium truncate" title={scenario.title}>
                            {scenario.title}
                          </p>
                          <p
                            className="text-xs text-muted-foreground truncate"
                            title={scenario.description}
                          >
                            {scenario.description}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {scenario.source_type === "web" ? (
                          <Badge variant="secondary" className="gap-1">
                            <Globe className="h-3 w-3" />
                            Web
                          </Badge>
                        ) : scenario.source_type === "bench" ? (
                          <Badge variant="secondary" className="gap-1">
                            <Database className="h-3 w-3" />
                            Bench
                          </Badge>
                        ) : (
                          <Badge variant="outline">{scenario.source_type}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {scenario.state ? (
                          <Badge variant="outline">{scenario.state}</Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {scenario.specialty ? (
                          <span className="text-sm">{scenario.specialty}</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {scenario.rubric_criteria?.length || 0} criteria
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Switch
                            checked={scenario.clinician_approved}
                            onCheckedChange={() => handleApprovalToggle(scenario)}
                            disabled={updating === scenario.scenario_id}
                          />
                          {scenario.clinician_approved ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
