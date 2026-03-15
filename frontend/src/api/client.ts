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
