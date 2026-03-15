import { useState, type FormEvent } from "react";

interface Props {
  onSubmit: (problem: string, file: File) => void;
  loading: boolean;
}

export default function ProblemForm({ onSubmit, loading }: Props) {
  const [problem, setProblem] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (problem.trim() && file) {
      onSubmit(problem, file);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="problem-form">
      <h2>Describe Your Problem</h2>

      <textarea
        value={problem}
        onChange={(e) => setProblem(e.target.value)}
        placeholder="e.g., Predict customer churn based on usage data..."
        rows={4}
        required
      />

      <div className="file-upload">
        <label htmlFor="csv-file">Upload CSV Dataset</label>
        <input
          id="csv-file"
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
        {file && <span className="file-name">{file.name}</span>}
      </div>

      <button type="submit" disabled={loading || !problem.trim() || !file}>
        {loading ? "Analyzing..." : "Get Recommendations"}
      </button>
    </form>
  );
}
