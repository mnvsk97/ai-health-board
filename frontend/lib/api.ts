import type {
  Run,
  CreateRunPayload,
  CreateRunResponse,
  GetTranscriptResponse,
  GetReportResponse,
  ListScenariosResponse,
  ListRunsResponse,
  StopRunResponse,
  SimulateChangePayload,
  SimulateChangeResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export async function createRun(payload: CreateRunPayload): Promise<CreateRunResponse> {
  return fetchAPI<CreateRunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRun(runId: string): Promise<Run> {
  return fetchAPI<Run>(`/runs/${runId}`);
}

export async function listRuns(status?: string, limit?: number): Promise<ListRunsResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", limit.toString());
  const query = params.toString();
  return fetchAPI<ListRunsResponse>(`/runs${query ? `?${query}` : ""}`);
}

export async function stopRun(runId: string): Promise<StopRunResponse> {
  return fetchAPI<StopRunResponse>(`/runs/${runId}/stop`, { method: "POST" });
}

export async function getTranscript(runId: string): Promise<GetTranscriptResponse> {
  return fetchAPI<GetTranscriptResponse>(`/runs/${runId}/transcript`);
}

export async function getReport(runId: string): Promise<GetReportResponse> {
  return fetchAPI<GetReportResponse>(`/runs/${runId}/report`);
}

export async function gradeRun(runId: string): Promise<GetReportResponse> {
  return fetchAPI<GetReportResponse>(`/runs/${runId}/grade`, { method: "POST" });
}

export async function listScenarios(): Promise<ListScenariosResponse> {
  return fetchAPI<ListScenariosResponse>("/scenarios");
}

export async function simulateGuidelineChange(
  payload: SimulateChangePayload
): Promise<SimulateChangeResponse> {
  return fetchAPI<SimulateChangeResponse>("/compliance/simulate-change", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ListGuidelinesResponse {
  guidelines: Guideline[];
}

export interface GetComplianceStatusResponse {
  target_id: string;
  status: ComplianceStatusType;
  reason: string | null;
  updated_at: number | null;
}

import type { Guideline, ComplianceStatusType } from "./types";

export async function listGuidelines(): Promise<ListGuidelinesResponse> {
  return fetchAPI<ListGuidelinesResponse>("/guidelines");
}

export async function getComplianceStatus(targetId: string = "default"): Promise<GetComplianceStatusResponse> {
  return fetchAPI<GetComplianceStatusResponse>(`/compliance/status?target_id=${targetId}`);
}

export interface AttackVector {
  attack_id: string;
  prompt: string;
  category: string;
  tags: string[];
  attempts: number;
  success_rate: number;
  severity_avg: number;
  last_used: number | null;
}

export interface ListAttacksResponse {
  attacks: AttackVector[];
}

export async function listAttacks(): Promise<ListAttacksResponse> {
  return fetchAPI<ListAttacksResponse>("/attacks");
}

export async function updateScenario(
  scenarioId: string,
  updates: { clinician_approved?: boolean }
): Promise<Scenario> {
  return fetchAPI<Scenario>(`/scenarios/${scenarioId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

import type {
  Scenario,
  BatchRun,
  CreateBatchRunPayload,
  CreateBatchRunResponse,
  ListBatchesResponse,
  StopBatchResponse,
} from "./types";

// =============================================================================
// Batch Run API Functions
// =============================================================================

export async function createBatchRun(
  payload: CreateBatchRunPayload = {}
): Promise<CreateBatchRunResponse> {
  return fetchAPI<CreateBatchRunResponse>("/batches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBatchRun(batchId: string): Promise<BatchRun> {
  return fetchAPI<BatchRun>(`/batches/${batchId}`);
}

export async function listBatches(
  status?: string,
  limit?: number
): Promise<ListBatchesResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", limit.toString());
  const query = params.toString();
  return fetchAPI<ListBatchesResponse>(`/batches${query ? `?${query}` : ""}`);
}

export async function stopBatchRun(batchId: string): Promise<StopBatchResponse> {
  return fetchAPI<StopBatchResponse>(`/batches/${batchId}/stop`, {
    method: "POST",
  });
}
