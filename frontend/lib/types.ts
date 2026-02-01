export type RunStatus = "pending" | "running" | "grading" | "completed" | "failed" | "canceled";
export type RunMode = "text_text" | "text_voice" | "voice_voice";
export type SourceType = "bench" | "web" | "trace" | "performance";
export type Severity = "critical" | "high" | "medium" | "low" | "none";
export type ComplianceStatusType = "valid" | "outdated" | "pending";
export type TranscriptRole = "tester" | "target" | "system";
export type UrgencyLevel = "emergent" | "urgent" | "routine";
export type Appropriateness = "appropriate" | "concerning" | "inappropriate";
export type PassFail = "pass" | "fail" | "needs_review";

export interface RubricCriterion {
  criterion: string;
  points: number;
  tags: string[];
}

export interface Scenario {
  scenario_id: string;
  title: string;
  description: string;
  source_type: SourceType;
  source_url: string | null;
  state: string | null;
  specialty: string | null;
  rubric_criteria: RubricCriterion[];
  clinician_approved: boolean;
}

export interface TranscriptEntry {
  role: TranscriptRole;
  content: string;
  timestamp: number;
}

export interface Run {
  run_id: string;
  status: RunStatus;
  scenario_ids: string[];
  mode: RunMode;
  room_url: string | null;
  room_name: string | null;
  room_token: string | null;
  started_at: number | null;
  updated_at: number | null;
}

// Stage 1: Scenario Context
export interface ScenarioContext {
  clinical_setting: string;
  patient_presentation: string;
  expected_behaviors: string[];
  red_flags: string[];
  urgency_level: UrgencyLevel;
  safety_critical_actions: string[];
}

// Stage 2: Turn Analysis
export interface TurnEvaluation {
  turn_index: number;
  role: string;
  content_summary: string;
  appropriateness: Appropriateness;
  reasoning: string;
  issues_identified: string[];
}

export interface TurnAnalysisResult {
  turn_evaluations: TurnEvaluation[];
  conversation_flow: string;
  critical_turns: number[];
}

// Stage 3: Rubric Scores
export interface CriterionEvaluation {
  criterion: string;
  score: number;
  max_score: number;
  evidence: string[];
  reasoning: string;
}

export interface RubricScores {
  criterion_evaluations: CriterionEvaluation[];
  total_score: number;
  max_total_score: number;
  overall_percentage: number;
}

// Stage 4a: Safety Audit
export interface SafetyViolation {
  violation_type: string;
  severity: Severity;
  description: string;
  turn_indices: number[];
  potential_harm: string;
}

export interface SafetyAudit {
  violations: SafetyViolation[];
  passed_safety_check: boolean;
  highest_severity: Severity;
  safety_score: number;
  recommendations: string[];
}

// Stage 4b: Quality Assessment
export interface QualityAssessment {
  empathy_score: number;
  empathy_evidence: string[];
  clarity_score: number;
  clarity_evidence: string[];
  completeness_score: number;
  completeness_evidence: string[];
  professionalism_score: number;
  overall_quality_score: number;
  strengths: string[];
  areas_for_improvement: string[];
}

// Stage 4c: Compliance Audit
export interface ComplianceViolation {
  violation_type: "licensure" | "scope" | "hipaa" | "consent" | "state_rule";
  description: string;
  severity: Severity;
  turn_indices: number[];
  regulation_reference: string;
}

export interface ComplianceAudit {
  violations: ComplianceViolation[];
  passed_compliance_check: boolean;
  highest_severity: Severity;
  compliance_score: number;
  licensure_verified: boolean;
  scope_appropriate: boolean;
  required_disclosures_made: string[];
  missing_disclosures: string[];
  recommendations: string[];
}

// Stage 5: Severity Result
export interface SeverityResult {
  overall_severity: Severity;
  break_type: string;
  severity_reasoning: string;
  contributing_factors: string[];
  recommended_action: string;
}

// Full Comprehensive Grading Result
export interface ComprehensiveGradingResult {
  // Metadata
  grader_model: string;
  scenario_id: string;
  grading_timestamp: number;

  // Stage outputs
  scenario_context: ScenarioContext;
  turn_analysis: TurnAnalysisResult;
  rubric_scores: RubricScores;
  safety_audit: SafetyAudit;
  quality_assessment: QualityAssessment;
  compliance_audit: ComplianceAudit | null;
  severity_result: SeverityResult;

  // Final summary
  break_type: string;
  severity: Severity;
  evaluations: LegacyEvaluation[];

  // Aggregated scores
  final_score: number;
  pass_fail: PassFail;
}

// Legacy format for backward compatibility
export interface LegacyEvaluation {
  criterion: string;
  points: number;
  points_earned: number;
  met: boolean;
  reasoning: string;
}

// Simplified grading result (for list views)
export interface GradingResult {
  grader_model: string;
  break_type: string;
  severity: Severity;
  evaluations: LegacyEvaluation[];
  // Optional comprehensive fields
  final_score?: number;
  pass_fail?: PassFail;
  scenario_context?: ScenarioContext;
  turn_analysis?: TurnAnalysisResult;
  rubric_scores?: RubricScores;
  safety_audit?: SafetyAudit;
  quality_assessment?: QualityAssessment;
  compliance_audit?: ComplianceAudit | null;
  severity_result?: SeverityResult;
}

export interface Guideline {
  guideline_id: string;
  source_url: string;
  state: string | null;
  specialty: string | null;
  version: string;
  hash: string;
  last_checked: number;
}

export interface ComplianceStatus {
  target_id: string;
  status: ComplianceStatusType;
  reason: string | null;
  updated_at: number;
}

export interface CreateRunPayload {
  scenario_ids: string[];
  mode: RunMode;
  agent_type: "intake" | "refill";
}

export interface CreateRunResponse {
  run_id: string;
  status: RunStatus;
}

export interface GetTranscriptResponse {
  run_id: string;
  transcript: TranscriptEntry[];
}

export interface GetReportResponse {
  run_id: string;
  grading: GradingResult;
}

export interface ListScenariosResponse {
  scenarios: Scenario[];
}

export interface SimulateChangePayload {
  guideline_id: string;
  target_id?: string;
}

export interface SimulateChangeResponse {
  status: "outdated";
  new_scenario: Scenario;
}

export interface ListRunsResponse {
  runs: Run[];
}

export interface StopRunResponse {
  status: "canceled";
}

// =============================================================================
// Batch Run Types
// =============================================================================

export type BatchRunStatus = "pending" | "running" | "completed" | "failed" | "canceled";

export interface BatchRun {
  batch_id: string;
  status: BatchRunStatus;
  scenario_ids: string[];
  child_run_ids: string[];
  concurrency: number;
  agent_type: string;
  turns: number;
  total_scenarios: number;
  completed_count: number;
  failed_count: number;
  canceled_count: number;
  started_at: number | null;
  completed_at: number | null;
  created_at: number | null;
}

export interface CreateBatchRunPayload {
  scenario_ids?: string[];
  agent_type?: string;
  concurrency?: number;
  turns?: number;
}

export interface CreateBatchRunResponse {
  batch_id: string;
  status: BatchRunStatus;
  total_scenarios: number;
}

export interface ListBatchesResponse {
  batches: BatchRun[];
}

export interface StopBatchResponse {
  status: "canceled";
  batch_id: string;
}
