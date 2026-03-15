import io

import pandas as pd

from models.schemas import ColumnProfile, DatasetProfile


def profile_dataset(file_bytes: bytes) -> DatasetProfile:
    """Parse a CSV file and return a structured profile of the dataset."""
    df = pd.read_csv(io.BytesIO(file_bytes))

    columns: list[ColumnProfile] = []
    for col in df.columns:
        series = df[col]
        is_numeric = pd.api.types.is_numeric_dtype(series)

        profile = ColumnProfile(
            name=col,
            dtype=_friendly_dtype(series),
            unique_count=int(series.nunique()),
            missing_pct=round(float(series.isna().mean()) * 100, 2),
            sample_values=[str(v) for v in series.dropna().head(5).tolist()],
            mean=round(float(series.mean()), 4) if is_numeric else None,
            std=round(float(series.std()), 4) if is_numeric else None,
            min=round(float(series.min()), 4) if is_numeric else None,
            max=round(float(series.max()), 4) if is_numeric else None,
        )
        columns.append(profile)

    return DatasetProfile(
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
    )


def _friendly_dtype(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Heuristic: if few unique values relative to total, treat as categorical
    if series.nunique() / max(len(series), 1) < 0.05:
        return "categorical"

    return "text"
