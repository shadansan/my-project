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
