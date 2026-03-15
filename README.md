# ML Advisor

A web app that analyzes your dataset and problem description, then suggests ML models, provides starter Python code, and recommends visualizations — powered by Azure OpenAI.

## Quick Start

```sh
# 1. Clone and set up backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in your Azure OpenAI credentials
uvicorn main:app --reload

# 2. Start frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, describe your problem, upload a CSV, and get recommendations.
