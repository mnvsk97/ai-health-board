"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Shield,
  ShieldAlert,
  Heart,
  MessageSquare,
  FileCheck,
  TrendingUp,
  AlertOctagon,
  Info,
} from "lucide-react";
import type { GradingResult, Severity, Appropriateness } from "@/lib/types";

interface GradingResultsProps {
  grading: GradingResult;
}

const severityConfig: Record<Severity, { label: string; variant: "critical" | "high" | "medium" | "low" | "pass"; color: string }> = {
  critical: { label: "Critical", variant: "critical", color: "text-red-500" },
  high: { label: "High", variant: "high", color: "text-orange-500" },
  medium: { label: "Medium", variant: "medium", color: "text-yellow-500" },
  low: { label: "Low", variant: "low", color: "text-blue-500" },
  none: { label: "None", variant: "pass", color: "text-green-500" },
};

const appropriatenessConfig: Record<Appropriateness, { icon: typeof CheckCircle; color: string }> = {
  appropriate: { icon: CheckCircle, color: "text-green-500" },
  concerning: { icon: AlertTriangle, color: "text-yellow-500" },
  inappropriate: { icon: XCircle, color: "text-red-500" },
};

function QualityGauge({ label, score, max = 10 }: { label: string; score: number; max?: number }) {
  const percentage = (score / max) * 100;
  const color = percentage >= 70 ? "bg-green-500" : percentage >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span>{label}</span>
          <span className="font-medium">{score.toFixed(1)}</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden bg-muted">
          <div className={cn("h-full transition-all duration-500", color)} style={{ width: `${percentage}%` }} />
        </div>
      </div>
    </div>
  );
}

export function GradingResults({ grading }: GradingResultsProps) {
  // Check if we have comprehensive data
  const hasComprehensiveData = grading.rubric_scores || grading.safety_audit || grading.quality_assessment;

  // Legacy evaluations fallback
  const totalPoints = grading.evaluations?.reduce((sum, e) => sum + e.points, 0) || 0;
  const earnedPoints = grading.evaluations?.reduce((sum, e) => sum + e.points_earned, 0) || 0;
  const passedCount = grading.evaluations?.filter((e) => e.met).length || 0;
  const failedCount = grading.evaluations?.filter((e) => !e.met).length || 0;
  const evalCount = grading.evaluations?.length || 1;
  const passPercent = (passedCount / evalCount) * 100;
  const failPercent = (failedCount / evalCount) * 100;

  // Comprehensive data
  const rubricScores = grading.rubric_scores;
  const safetyAudit = grading.safety_audit;
  const qualityAssessment = grading.quality_assessment;
  const turnAnalysis = grading.turn_analysis;
  const complianceAudit = grading.compliance_audit;
  const severityResult = grading.severity_result;

  const passFail = grading.pass_fail || (passedCount > failedCount ? "pass" : "fail");
  const finalScore = grading.final_score ?? (totalPoints > 0 ? (earnedPoints / totalPoints) * 100 : 0);

  return (
    <div className="space-y-4">
      {/* Overall Result Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {passFail === "pass" ? (
                <div className="p-2 rounded-full bg-green-500/10">
                  <CheckCircle className="h-6 w-6 text-green-500" />
                </div>
              ) : passFail === "needs_review" ? (
                <div className="p-2 rounded-full bg-yellow-500/10">
                  <AlertTriangle className="h-6 w-6 text-yellow-500" />
                </div>
              ) : (
                <div className="p-2 rounded-full bg-red-500/10">
                  <XCircle className="h-6 w-6 text-red-500" />
                </div>
              )}
              <div>
                <CardTitle className="text-lg">
                  {passFail === "pass" ? "Test Passed" : passFail === "needs_review" ? "Needs Review" : "Test Failed"}
                </CardTitle>
                <CardDescription>
                  Score: {finalScore.toFixed(1)}% | {grading.grader_model}
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={severityConfig[grading.severity]?.variant || "medium"}>
                {severityConfig[grading.severity]?.label || grading.severity} Severity
              </Badge>
              {grading.break_type !== "none" && grading.break_type && (
                <Badge variant="destructive">
                  {grading.break_type.replace(/_/g, " ")}
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Score Overview */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{finalScore.toFixed(0)}%</div>
              <div className="text-xs text-muted-foreground">Overall Score</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-green-500/10">
              <div className="text-2xl font-bold text-green-600">{passedCount}</div>
              <div className="text-xs text-muted-foreground">Passed</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-red-500/10">
              <div className="text-2xl font-bold text-red-600">{failedCount}</div>
              <div className="text-xs text-muted-foreground">Failed</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{safetyAudit?.safety_score ?? 100}</div>
              <div className="text-xs text-muted-foreground">Safety Score</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-3 rounded-full overflow-hidden flex bg-muted">
            <div className="bg-green-500 transition-all duration-500" style={{ width: `${passPercent}%` }} />
            <div className="bg-red-500 transition-all duration-500" style={{ width: `${failPercent}%` }} />
          </div>
        </CardContent>
      </Card>

      {/* Detailed Results Tabs */}
      {hasComprehensiveData ? (
        <Card>
          <Tabs defaultValue="rubric" className="w-full">
            <CardHeader className="pb-0">
              <TabsList className="grid w-full grid-cols-5">
                <TabsTrigger value="rubric" className="text-xs">
                  <FileCheck className="h-3 w-3 mr-1" />
                  Rubric
                </TabsTrigger>
                <TabsTrigger value="safety" className="text-xs">
                  <Shield className="h-3 w-3 mr-1" />
                  Safety
                </TabsTrigger>
                <TabsTrigger value="quality" className="text-xs">
                  <Heart className="h-3 w-3 mr-1" />
                  Quality
                </TabsTrigger>
                <TabsTrigger value="turns" className="text-xs">
                  <MessageSquare className="h-3 w-3 mr-1" />
                  Turns
                </TabsTrigger>
                <TabsTrigger value="compliance" className="text-xs">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Compliance
                </TabsTrigger>
              </TabsList>
            </CardHeader>

            <CardContent className="pt-4">
              {/* Rubric Tab */}
              <TabsContent value="rubric" className="mt-0">
                <ScrollArea className="h-[400px] pr-4">
                  {rubricScores ? (
                    <div className="space-y-4">
                      <div className="p-3 rounded-lg bg-muted/50">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">Overall Score</span>
                          <span className="text-lg font-bold">{rubricScores.overall_percentage.toFixed(1)}%</span>
                        </div>
                        <Progress value={rubricScores.overall_percentage} className="mt-2" />
                        <div className="text-xs text-muted-foreground mt-1">
                          {rubricScores.total_score} / {rubricScores.max_total_score} points
                        </div>
                      </div>
                      <div className="space-y-3">
                        {rubricScores.criterion_evaluations.map((evaluation, index) => (
                          <div
                            key={index}
                            className={cn(
                              "p-3 rounded-lg border",
                              evaluation.score >= evaluation.max_score * 0.7
                                ? "border-green-500/30 bg-green-500/5"
                                : evaluation.score >= evaluation.max_score * 0.4
                                ? "border-yellow-500/30 bg-yellow-500/5"
                                : "border-red-500/30 bg-red-500/5"
                            )}
                          >
                            <div className="flex items-start gap-3">
                              {evaluation.score >= evaluation.max_score * 0.7 ? (
                                <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
                              ) : evaluation.score >= evaluation.max_score * 0.4 ? (
                                <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5 shrink-0" />
                              ) : (
                                <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-medium">{evaluation.criterion}</span>
                                  <span className="text-sm text-muted-foreground shrink-0">
                                    {evaluation.score}/{evaluation.max_score}
                                  </span>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">{evaluation.reasoning}</p>
                                {evaluation.evidence.length > 0 && (
                                  <div className="mt-2 space-y-1">
                                    {evaluation.evidence.map((e, i) => (
                                      <div key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                                        <span className="text-primary">•</span>
                                        <span>{e}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {grading.evaluations?.map((evaluation, index) => (
                        <div
                          key={index}
                          className={cn(
                            "p-3 rounded-lg border",
                            evaluation.met ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            {evaluation.met ? (
                              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium">{evaluation.criterion}</span>
                                <span className="text-sm text-muted-foreground shrink-0">
                                  {evaluation.points_earned}/{evaluation.points} pts
                                </span>
                              </div>
                              <p className="mt-1 text-sm text-muted-foreground">{evaluation.reasoning}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Safety Tab */}
              <TabsContent value="safety" className="mt-0">
                <ScrollArea className="h-[400px] pr-4">
                  {safetyAudit ? (
                    <div className="space-y-4">
                      {/* Safety Overview */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className={cn(
                          "p-4 rounded-lg border",
                          safetyAudit.passed_safety_check
                            ? "border-green-500/30 bg-green-500/5"
                            : "border-red-500/30 bg-red-500/5"
                        )}>
                          <div className="flex items-center gap-2">
                            {safetyAudit.passed_safety_check ? (
                              <Shield className="h-5 w-5 text-green-500" />
                            ) : (
                              <ShieldAlert className="h-5 w-5 text-red-500" />
                            )}
                            <span className="font-medium">
                              {safetyAudit.passed_safety_check ? "Safety Check Passed" : "Safety Check Failed"}
                            </span>
                          </div>
                        </div>
                        <div className="p-4 rounded-lg border bg-muted/50">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Safety Score</span>
                            <span className="text-2xl font-bold">{safetyAudit.safety_score}</span>
                          </div>
                        </div>
                      </div>

                      {/* Violations */}
                      {safetyAudit.violations.length > 0 ? (
                        <div className="space-y-3">
                          <h4 className="font-medium flex items-center gap-2">
                            <AlertOctagon className="h-4 w-4 text-red-500" />
                            Safety Violations ({safetyAudit.violations.length})
                          </h4>
                          {safetyAudit.violations.map((violation, index) => (
                            <div key={index} className="p-3 rounded-lg border border-red-500/30 bg-red-500/5">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">{violation.violation_type.replace(/_/g, " ")}</span>
                                    <Badge variant={severityConfig[violation.severity]?.variant || "medium"} className="text-xs">
                                      {violation.severity}
                                    </Badge>
                                  </div>
                                  <p className="mt-1 text-sm text-muted-foreground">{violation.description}</p>
                                  {violation.potential_harm && (
                                    <p className="mt-2 text-xs text-red-500">
                                      Potential harm: {violation.potential_harm}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-6 text-center text-muted-foreground">
                          <Shield className="h-12 w-12 mx-auto mb-2 text-green-500" />
                          <p>No safety violations detected</p>
                        </div>
                      )}

                      {/* Recommendations */}
                      {safetyAudit.recommendations.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-medium flex items-center gap-2">
                            <Info className="h-4 w-4" />
                            Recommendations
                          </h4>
                          <ul className="space-y-1">
                            {safetyAudit.recommendations.map((rec, i) => (
                              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                <span className="text-primary">•</span>
                                <span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 text-center text-muted-foreground">
                      <Shield className="h-12 w-12 mx-auto mb-2" />
                      <p>No safety audit data available</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Quality Tab */}
              <TabsContent value="quality" className="mt-0">
                <ScrollArea className="h-[400px] pr-4">
                  {qualityAssessment ? (
                    <div className="space-y-6">
                      {/* Quality Scores */}
                      <div className="p-4 rounded-lg bg-muted/50">
                        <div className="flex items-center justify-between mb-4">
                          <span className="font-medium">Overall Quality</span>
                          <span className="text-2xl font-bold">{qualityAssessment.overall_quality_score.toFixed(1)}/10</span>
                        </div>
                        <div className="space-y-4">
                          <QualityGauge label="Empathy" score={qualityAssessment.empathy_score} />
                          <QualityGauge label="Clarity" score={qualityAssessment.clarity_score} />
                          <QualityGauge label="Completeness" score={qualityAssessment.completeness_score} />
                          <QualityGauge label="Professionalism" score={qualityAssessment.professionalism_score} />
                        </div>
                      </div>

                      {/* Strengths */}
                      {qualityAssessment.strengths.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-medium flex items-center gap-2 text-green-600">
                            <CheckCircle className="h-4 w-4" />
                            Strengths
                          </h4>
                          <ul className="space-y-1">
                            {qualityAssessment.strengths.map((s, i) => (
                              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                <span className="text-green-500">+</span>
                                <span>{s}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Areas for Improvement */}
                      {qualityAssessment.areas_for_improvement.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-medium flex items-center gap-2 text-yellow-600">
                            <TrendingUp className="h-4 w-4" />
                            Areas for Improvement
                          </h4>
                          <ul className="space-y-1">
                            {qualityAssessment.areas_for_improvement.map((a, i) => (
                              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                <span className="text-yellow-500">-</span>
                                <span>{a}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 text-center text-muted-foreground">
                      <Heart className="h-12 w-12 mx-auto mb-2" />
                      <p>No quality assessment data available</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Turns Tab */}
              <TabsContent value="turns" className="mt-0">
                <ScrollArea className="h-[400px] pr-4">
                  {turnAnalysis ? (
                    <div className="space-y-4">
                      {/* Conversation Flow */}
                      {turnAnalysis.conversation_flow && (
                        <div className="p-3 rounded-lg bg-muted/50">
                          <h4 className="font-medium mb-2">Conversation Flow</h4>
                          <p className="text-sm text-muted-foreground">{turnAnalysis.conversation_flow}</p>
                        </div>
                      )}

                      {/* Turn by Turn */}
                      <div className="space-y-2">
                        {turnAnalysis.turn_evaluations.map((turn, index) => {
                          const config = appropriatenessConfig[turn.appropriateness];
                          const Icon = config?.icon || Info;
                          const isCritical = turnAnalysis.critical_turns.includes(turn.turn_index);
                          return (
                            <div
                              key={index}
                              className={cn(
                                "p-3 rounded-lg border",
                                isCritical && "ring-2 ring-yellow-500/50",
                                turn.appropriateness === "appropriate"
                                  ? "border-green-500/20 bg-green-500/5"
                                  : turn.appropriateness === "concerning"
                                  ? "border-yellow-500/20 bg-yellow-500/5"
                                  : "border-red-500/20 bg-red-500/5"
                              )}
                            >
                              <div className="flex items-start gap-3">
                                <Icon className={cn("h-4 w-4 mt-1 shrink-0", config?.color || "text-muted-foreground")} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="text-xs capitalize">
                                      {turn.role}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">Turn {turn.turn_index + 1}</span>
                                    {isCritical && (
                                      <Badge variant="warning" className="text-xs">Critical</Badge>
                                    )}
                                  </div>
                                  <p className="mt-1 text-sm">{turn.content_summary}</p>
                                  <p className="mt-1 text-xs text-muted-foreground">{turn.reasoning}</p>
                                  {turn.issues_identified.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-1">
                                      {turn.issues_identified.map((issue, i) => (
                                        <Badge key={i} variant="destructive" className="text-xs">
                                          {issue}
                                        </Badge>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-muted-foreground">
                      <MessageSquare className="h-12 w-12 mx-auto mb-2" />
                      <p>No turn analysis data available</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Compliance Tab */}
              <TabsContent value="compliance" className="mt-0">
                <ScrollArea className="h-[400px] pr-4">
                  {complianceAudit ? (
                    <div className="space-y-4">
                      {/* Compliance Overview */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className={cn(
                          "p-4 rounded-lg border",
                          complianceAudit.passed_compliance_check
                            ? "border-green-500/30 bg-green-500/5"
                            : "border-red-500/30 bg-red-500/5"
                        )}>
                          <div className="flex items-center gap-2">
                            {complianceAudit.passed_compliance_check ? (
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-500" />
                            )}
                            <span className="font-medium">
                              {complianceAudit.passed_compliance_check ? "Compliant" : "Non-Compliant"}
                            </span>
                          </div>
                        </div>
                        <div className="p-4 rounded-lg border bg-muted/50">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Compliance Score</span>
                            <span className="text-2xl font-bold">{complianceAudit.compliance_score}</span>
                          </div>
                        </div>
                      </div>

                      {/* Status Checks */}
                      <div className="grid grid-cols-2 gap-2">
                        <div className={cn(
                          "p-3 rounded-lg flex items-center gap-2",
                          complianceAudit.licensure_verified ? "bg-green-500/10" : "bg-muted/50"
                        )}>
                          {complianceAudit.licensure_verified ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-muted-foreground" />
                          )}
                          <span className="text-sm">Licensure Verified</span>
                        </div>
                        <div className={cn(
                          "p-3 rounded-lg flex items-center gap-2",
                          complianceAudit.scope_appropriate ? "bg-green-500/10" : "bg-red-500/10"
                        )}>
                          {complianceAudit.scope_appropriate ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                          <span className="text-sm">Within Scope</span>
                        </div>
                      </div>

                      {/* Violations */}
                      {complianceAudit.violations.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="font-medium">Violations ({complianceAudit.violations.length})</h4>
                          {complianceAudit.violations.map((violation, index) => (
                            <div key={index} className="p-3 rounded-lg border border-red-500/30 bg-red-500/5">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge variant="outline" className="text-xs uppercase">
                                  {violation.violation_type}
                                </Badge>
                                <Badge variant={severityConfig[violation.severity]?.variant || "medium"} className="text-xs">
                                  {violation.severity}
                                </Badge>
                              </div>
                              <p className="text-sm">{violation.description}</p>
                              {violation.regulation_reference && (
                                <p className="mt-1 text-xs text-muted-foreground">
                                  Ref: {violation.regulation_reference}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Missing Disclosures */}
                      {complianceAudit.missing_disclosures.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-medium text-yellow-600">Missing Disclosures</h4>
                          <ul className="space-y-1">
                            {complianceAudit.missing_disclosures.map((d, i) => (
                              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                <AlertTriangle className="h-3 w-3 text-yellow-500 mt-1 shrink-0" />
                                <span>{d}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 text-center text-muted-foreground">
                      <TrendingUp className="h-12 w-12 mx-auto mb-2" />
                      <p>No compliance audit data available</p>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>
            </CardContent>
          </Tabs>
        </Card>
      ) : (
        /* Legacy Criterion List */
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Criteria Evaluation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {grading.evaluations?.map((evaluation, index) => (
                <div
                  key={index}
                  className={cn(
                    "p-3 rounded-lg border",
                    evaluation.met ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"
                  )}
                >
                  <div className="flex items-start gap-3">
                    {evaluation.met ? (
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{evaluation.criterion}</span>
                        <span className="text-sm text-muted-foreground shrink-0">
                          {evaluation.points_earned}/{evaluation.points} pts
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{evaluation.reasoning}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Severity Reasoning */}
      {severityResult && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className={severityConfig[severityResult.overall_severity]?.color || ""} />
              Severity Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{severityResult.severity_reasoning}</p>
            {severityResult.contributing_factors.length > 0 && (
              <div className="mt-3">
                <h4 className="text-sm font-medium mb-2">Contributing Factors:</h4>
                <ul className="space-y-1">
                  {severityResult.contributing_factors.map((f, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-primary">•</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {severityResult.recommended_action && (
              <div className="mt-3 p-3 rounded-lg bg-muted/50">
                <span className="text-sm font-medium">Recommended Action: </span>
                <span className="text-sm text-muted-foreground">{severityResult.recommended_action}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
