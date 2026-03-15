from models.schemas import (
    AnalyzeResponse,
    DatasetProfile,
    ModelSuggestion,
    VizSuggestion,
)
from services.llm import chat_json

SYSTEM_PROMPT = """\
You are an expert data scientist advisor. Given a problem description and a \
dataset profile, you suggest the best ML models, provide starter Python code, \
and recommend visualizations.

Always respond with valid JSON matching this schema:
{
  "model_suggestions": [
    {
      "name": "Human-readable model name",
      "model_type": "classification | regression | clustering | dimensionality_reduction | time_series",
      "reason": "Why this model fits the problem and data",
      "pros": ["advantage 1", "advantage 2"],
      "cons": ["limitation 1"],
      "code": "Complete runnable Python code snippet using scikit-learn or similar"
    }
  ],
  "viz_suggestions": [
    {
      "chart_type": "e.g. scatter plot, heatmap, bar chart",
      "description": "What insight this visualization reveals",
      "code": "Complete runnable Python code using matplotlib/seaborn/plotly"
    }
  ]
}

Guidelines:
- Suggest 2-4 models, ordered by relevance.
- Code must be complete: include imports, data loading (assume df is a pandas DataFrame), \
  training, and evaluation.
- Suggest 2-3 visualizations that help understand the data or model results.
- Use scikit-learn for models when possible.
- Use plotly for interactive charts, matplotlib/seaborn for static ones.
"""


def build_user_prompt(problem: str, profile: DatasetProfile) -> str:
    columns_desc = "\n".join(
        f"  - {c.name} ({c.dtype}): {c.unique_count} unique, "
        f"{c.missing_pct}% missing, samples={c.sample_values[:3]}"
        for c in profile.columns
    )
    return (
        f"Problem: {problem}\n\n"
        f"Dataset: {profile.row_count} rows × {profile.column_count} columns\n"
        f"Columns:\n{columns_desc}"
    )


def get_recommendations(
    problem: str, profile: DatasetProfile
) -> AnalyzeResponse:
    user_prompt = build_user_prompt(problem, profile)
    result = chat_json(SYSTEM_PROMPT, user_prompt)

    model_suggestions = [
        ModelSuggestion(**m) for m in result.get("model_suggestions", [])
    ]
    viz_suggestions = [
        VizSuggestion(**v) for v in result.get("viz_suggestions", [])
    ]

    return AnalyzeResponse(
        dataset_profile=profile,
        model_suggestions=model_suggestions,
        viz_suggestions=viz_suggestions,
    )
