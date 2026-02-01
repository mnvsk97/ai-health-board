export type RunStatus = "pending" | "running" | "grading" | "completed" | "failed" | "canceled";
export type RunMode = "text_text" | "text_voice" | "voice_voice";
export type SourceType = "bench" | "web" | "trace" | "performance";
export type Severity = "critical" | "high" | "medium" | "low";
export type ComplianceStatusType = "valid" | "outdated" | "pending";
export type TranscriptRole = "tester" | "target" | "system";

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

export interface CriterionEvaluation {
  criterion: string;
  points: number;
  points_earned: number;
  met: boolean;
  reasoning: string;
}

export interface GradingResult {
  grader_model: string;
  break_type: string;
  severity: Severity;
  evaluations: CriterionEvaluation[];
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
