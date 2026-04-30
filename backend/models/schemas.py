from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    unique_count: int
    missing_pct: float
    sample_values: list[str]
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]


class ModelSuggestion(BaseModel):
    name: str
    model_type: str
    reason: str
    pros: list[str]
    cons: list[str]
    code: str


class VizSuggestion(BaseModel):
    chart_type: str
    description: str
    code: str


class AnalyzeResponse(BaseModel):
    dataset_profile: DatasetProfile
    model_suggestions: list[ModelSuggestion]
    viz_suggestions: list[VizSuggestion]


# ── DLP Diagnostics ──


class DlpRootCause(BaseModel):
    rule: str
    issue: str
    impact: str
    severity: str  # "critical" | "warning" | "info"
    predicates: list[str] = []  # conditions/predicates configured on this rule


class DlpEvidence(BaseModel):
    config: list[str]
    logs: list[str]
    code: list[str]


class DlpRecommendation(BaseModel):
    priority: int
    severity: str  # "critical" | "warning" | "info"
    title: str
    description: str
    action: str | None = None


class EventTrend(BaseModel):
    date: str
    count: int


class DlpDiagnosticsResponse(BaseModel):
    summary: str
    confidence: str  # "High" | "Medium" | "Low"
    root_causes: list[DlpRootCause]
    evidence: DlpEvidence
    recommendations: list[DlpRecommendation]
    unknowns: list[str]
    event_trend: list[EventTrend]
