import type { ModelSuggestion } from "../api/client";
import CodeViewer from "./CodeViewer";

interface Props {
  suggestions: ModelSuggestion[];
}

export default function ModelCards({ suggestions }: Props) {
  if (!suggestions.length) return null;

  return (
    <section className="model-cards">
      <h2>Recommended Models</h2>
      <div className="cards-grid">
        {suggestions.map((model, i) => (
          <div key={i} className="card">
            <div className="card-header">
              <h3>{model.name}</h3>
              <span className="badge">{model.model_type}</span>
            </div>

            <p className="reason">{model.reason}</p>

            <div className="pros-cons">
              <div className="pros">
                <h4>✅ Pros</h4>
                <ul>
                  {model.pros.map((p, j) => (
                    <li key={j}>{p}</li>
                  ))}
                </ul>
              </div>
              <div className="cons">
                <h4>⚠️ Cons</h4>
                <ul>
                  {model.cons.map((c, j) => (
                    <li key={j}>{c}</li>
                  ))}
                </ul>
              </div>
            </div>

            <CodeViewer code={model.code} />
          </div>
        ))}
      </div>
    </section>
  );
}
