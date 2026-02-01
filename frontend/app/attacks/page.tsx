"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Crosshair,
  RefreshCw,
  TrendingUp,
  Target,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listAttacks, type AttackVector } from "@/lib/api";

const categoryColors: Record<string, string> = {
  symptom_escalation: "bg-red-500",
  emergency_prompting: "bg-orange-500",
  boundary_violation: "bg-yellow-500",
  authority_challenge: "bg-purple-500",
  social_engineering: "bg-blue-500",
};

const categoryLabels: Record<string, string> = {
  symptom_escalation: "Symptom Escalation",
  emergency_prompting: "Emergency Prompting",
  boundary_violation: "Boundary Violation",
  authority_challenge: "Authority Challenge",
  social_engineering: "Social Engineering",
};

export default function AttacksPage() {
  const [attacks, setAttacks] = useState<AttackVector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listAttacks();
      setAttacks(response.attacks);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load attack vectors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatLastUsed = (timestamp: number | null) => {
    if (!timestamp) return "Never";
    const diff = Date.now() / 1000 - timestamp;
    const hours = Math.floor(diff / 3600);
    if (hours < 1) return "< 1 hour ago";
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const totalAttempts = attacks.reduce((sum, a) => sum + a.attempts, 0);
  const avgSuccessRate =
    attacks.length > 0
      ? attacks.reduce((sum, a) => sum + a.success_rate, 0) / attacks.length
      : 0;
  const avgSeverity =
    attacks.length > 0
      ? attacks.reduce((sum, a) => sum + a.severity_avg, 0) / attacks.length
      : 0;

  // Group by category for stats
  const categories = attacks.reduce((acc, attack) => {
    const cat = attack.category || "unknown";
    if (!acc[cat]) acc[cat] = 0;
    acc[cat]++;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-8 py-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Attack Vectors</h1>
          <p className="text-sm text-muted-foreground">
            View adversarial attack patterns and their effectiveness
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
                  <Crosshair className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{attacks.length}</p>
                  <p className="text-xs text-muted-foreground">Total Vectors</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Target className="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{totalAttempts}</p>
                  <p className="text-xs text-muted-foreground">Total Attempts</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{(avgSuccessRate * 100).toFixed(0)}%</p>
                  <p className="text-xs text-muted-foreground">Avg Success Rate</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-orange-500/10">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{avgSeverity.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">Avg Severity</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Category Distribution */}
        {Object.keys(categories).length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Category Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {Object.entries(categories).map(([cat, count]) => (
                  <Badge
                    key={cat}
                    variant="secondary"
                    className="gap-2 py-1 px-3"
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${categoryColors[cat] || "bg-gray-500"}`}
                    />
                    {categoryLabels[cat] || cat}
                    <span className="font-bold">{count}</span>
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error State */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="py-4">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Attack Vectors Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Crosshair className="h-5 w-5" />
              Attack Vector Library
            </CardTitle>
            <CardDescription>
              Adversarial prompts used to test agent robustness
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-16 bg-muted rounded" />
                ))}
              </div>
            ) : attacks.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <Crosshair className="h-12 w-12 mx-auto mb-4" />
                <p>No attack vectors found</p>
                <p className="text-sm mt-1">
                  Attack vectors are generated during test runs
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground w-[40%]">
                      Prompt
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Category
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-center">
                      Attempts
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
                      Success Rate
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-center">
                      Severity
                    </TableHead>
                    <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-right">
                      Last Used
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attacks.map((attack) => (
                    <TableRow key={attack.attack_id}>
                      <TableCell>
                        <p
                          className="text-sm font-mono truncate max-w-[400px]"
                          title={attack.prompt}
                        >
                          {attack.prompt}
                        </p>
                        {attack.tags.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {attack.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {attack.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{attack.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className="gap-1"
                        >
                          <span
                            className={`w-2 h-2 rounded-full ${
                              categoryColors[attack.category] || "bg-gray-500"
                            }`}
                          />
                          {categoryLabels[attack.category] || attack.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="font-medium">{attack.attempts}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress
                            value={attack.success_rate * 100}
                            className="w-16 h-2"
                          />
                          <span className="text-sm">
                            {(attack.success_rate * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant={
                            attack.severity_avg >= 0.7
                              ? "critical"
                              : attack.severity_avg >= 0.4
                              ? "warning"
                              : "secondary"
                          }
                        >
                          {attack.severity_avg.toFixed(2)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">
                        <div className="flex items-center justify-end gap-1">
                          <Clock className="h-3 w-3" />
                          <span className="text-sm">{formatLastUsed(attack.last_used)}</span>
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
