import { useState } from "react";
import ProblemForm from "./ProblemForm";
import DatasetOverview from "./DatasetOverview";
import ModelCards from "./ModelCards";
import VizSuggestions from "./VizSuggestions";
import { analyze, type AnalyzeResponse } from "../api/client";

export default function MlAdvisor() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const handleSubmit = async (problem: string, file: File) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyze(problem, file);
      setResult(data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <header>
        <h1>🧠 ML Advisor</h1>
        <p>Describe your problem, upload data, get model recommendations</p>
      </header>

      <main>
        <ProblemForm onSubmit={handleSubmit} loading={loading} />

        {error && <div className="error">{error}</div>}

        {result && (
          <div className="results">
            <DatasetOverview profile={result.dataset_profile} />
            <ModelCards suggestions={result.model_suggestions} />
            <VizSuggestions suggestions={result.viz_suggestions} />
          </div>
        )}
      </main>
    </>
  );
}
