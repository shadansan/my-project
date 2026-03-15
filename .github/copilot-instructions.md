# Copilot Instructions

## Build & Run

```sh
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # runs on :8000

# Frontend
cd frontend
npm install
npm run dev                        # runs on :5173
npm run build                      # production build
```

### Environment Variables (backend)

Copy `.env.example` to `.env` and fill in:
- `AZURE_OPENAI_API_KEY` — Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` — e.g. `https://<resource>.openai.azure.com`
- `AZURE_OPENAI_DEPLOYMENT` — deployment name (default: `gpt-4o`)

## Architecture

- **`backend/`** — FastAPI server
  - `services/dataset.py` — CSV parsing & profiling (pandas). Returns `DatasetProfile` with column types, stats, missing %.
  - `services/llm.py` — Azure OpenAI client. Sends structured prompts, expects JSON responses.
  - `services/advisor.py` — Orchestrator. Builds prompt from dataset profile + problem description, parses LLM response into `ModelSuggestion` and `VizSuggestion`.
  - `routers/analyze.py` — Single `POST /api/analyze` endpoint (multipart: problem + CSV file).
  - `models/schemas.py` — All Pydantic request/response models.

- **`frontend/`** — React + TypeScript (Vite)
  - `src/api/client.ts` — Typed API client (axios).
  - `src/components/ProblemForm.tsx` — Problem input + CSV upload.
  - `src/components/ModelCards.tsx` — Renders model suggestions with pros/cons.
  - `src/components/CodeViewer.tsx` — Syntax-highlighted Python code with copy button.
  - `src/components/VizSuggestions.tsx` — Visualization recommendations with code.
  - `src/components/DatasetOverview.tsx` — Dataset profile table.

## Conventions

- Backend schemas are defined once in `models/schemas.py` and shared across all services.
- The LLM service always uses `response_format: json_object` to get parseable JSON back.
- Frontend types in `api/client.ts` mirror the backend Pydantic models — keep them in sync.
- All LLM prompts live in `services/advisor.py` as module-level constants.
