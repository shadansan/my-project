import type { VizSuggestion } from "../api/client";
import CodeViewer from "./CodeViewer";

interface Props {
  suggestions: VizSuggestion[];
}

export default function VizSuggestions({ suggestions }: Props) {
  if (!suggestions.length) return null;

  return (
    <section className="viz-suggestions">
      <h2>Visualization Suggestions</h2>
      <div className="cards-grid">
        {suggestions.map((viz, i) => (
          <div key={i} className="card">
            <div className="card-header">
              <h3>{viz.chart_type}</h3>
            </div>
            <p className="reason">{viz.description}</p>
            <CodeViewer code={viz.code} />
          </div>
        ))}
      </div>
    </section>
  );
}
