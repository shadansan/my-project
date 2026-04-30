import axios from "axios";

const api = axios.create({ baseURL: "http://localhost:8000/api" });

export interface ColumnProfile {
  name: string;
  dtype: string;
  unique_count: number;
  missing_pct: number;
  sample_values: string[];
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
}

export interface ModelSuggestion {
  name: string;
  model_type: string;
  reason: string;
  pros: string[];
  cons: string[];
  code: string;
}

export interface VizSuggestion {
  chart_type: string;
  description: string;
  code: string;
}

export interface AnalyzeResponse {
  dataset_profile: DatasetProfile;
  model_suggestions: ModelSuggestion[];
  viz_suggestions: VizSuggestion[];
}

export async function analyze(
  problem: string,
  file: File
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("problem", problem);
  form.append("file", file);
  const { data } = await api.post<AnalyzeResponse>("/analyze", form);
  return data;
}

/* ── DLP Diagnostics types ── */

export interface DlpDiagnosticsRequest {
  tenantId: string;
  problemDescription: string;
  timeframe?: string;
  workload?: string;
  policyName?: string;
}

export interface DlpRootCause {
  rule: string;
  issue: string;
  impact: string;
  severity: "critical" | "warning" | "info";
  predicates: string[];
}

export interface DlpEvidence {
  config: string[];
  logs: string[];
  code: string[];
}

export interface DlpRecommendation {
  priority: number;
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  action?: string;
}

export interface DlpDiagnosticsResponse {
  summary: string;
  confidence: "High" | "Medium" | "Low";
  root_causes: DlpRootCause[];
  evidence: DlpEvidence;
  recommendations: DlpRecommendation[];
  unknowns: string[];
  event_trend: { date: string; count: number }[];
}

export async function runDlpDiagnostics(
  request: DlpDiagnosticsRequest,
  file: File
): Promise<DlpDiagnosticsResponse> {
  const form = new FormData();
  form.append("tenant_id", request.tenantId);
  form.append("problem_description", request.problemDescription);
  if (request.timeframe) form.append("timeframe", request.timeframe);
  if (request.workload) form.append("workload", request.workload);
  if (request.policyName) form.append("policy_name", request.policyName);
  form.append("file", file);
  const { data } = await api.post<DlpDiagnosticsResponse>("/dlp/diagnose", form);
  return data;
}
