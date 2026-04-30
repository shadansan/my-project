from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models.schemas import DlpDiagnosticsResponse
from services.dlp_diagnostics import run_diagnostics

router = APIRouter()


@router.post("/dlp/diagnose", response_model=DlpDiagnosticsResponse)
async def diagnose_dlp(
    tenant_id: str = Form(...),
    problem_description: str = Form(...),
    file: UploadFile = File(...),
    timeframe: str | None = Form(None),
    workload: str | None = Form(None),
    policy_name: str | None = Form(None),
) -> DlpDiagnosticsResponse:
    """Run real DLP diagnostics on an uploaded config ZIP."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported.")

    contents = await file.read()

    try:
        result = run_diagnostics(
            zip_bytes=contents,
            tenant_id=tenant_id,
            problem_description=problem_description,
            timeframe=timeframe,
            workload=workload,
            policy_name=policy_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {e}")

    return result
