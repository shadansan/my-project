import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models.schemas import AnalyzeResponse
from services.advisor import get_recommendations
from services.dataset import profile_dataset
from services.mock_advisor import get_mock_recommendations

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _is_demo_mode() -> bool:
    return not os.environ.get("AZURE_OPENAI_API_KEY")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    problem: str = Form(..., description="Description of the ML problem to solve"),
    file: UploadFile = File(..., description="CSV dataset file"),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50 MB).")

    try:
        profile = profile_dataset(contents)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse CSV: {e}")

    if _is_demo_mode():
        return get_mock_recommendations(problem, profile)

    try:
        result = get_recommendations(problem, profile)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")

    return result


@router.get("/mode")
async def get_mode():
    return {"mode": "demo" if _is_demo_mode() else "live"}
