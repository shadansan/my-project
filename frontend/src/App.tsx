import { useState } from "react";
import "./App.css";
import ProblemForm from "./components/ProblemForm";
import DatasetOverview from "./components/DatasetOverview";
import ModelCards from "./components/ModelCards";
import VizSuggestions from "./components/VizSuggestions";
import { analyze, type AnalyzeResponse } from "./api/client";

function App() {
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
    <div className="app">
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
    </div>
  );
}

export default App;
