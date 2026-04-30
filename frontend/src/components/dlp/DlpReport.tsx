import { useState } from "react";
import type { DlpDiagnosticsResponse } from "../../api/client";

interface Props {
  report: DlpDiagnosticsResponse;
}

const severityIcon: Record<string, string> = {
  critical: "🔴",
  warning: "🟡",
  info: "🔵",
};

const confidenceStyle: Record<string, { background: string; color: string }> = {
  High:   { background: "var(--success-bg)", color: "var(--success)" },
  Medium: { background: "var(--warning-bg)", color: "var(--warning)" },
  Low:    { background: "var(--danger-bg)",  color: "var(--danger)"  },
};

export default function DlpReport({ report }: Props) {
  return (
    <div className="dlp-report">
      {/* Summary */}
      <section className="card">
        <div className="card-header">
          <h3>Summary</h3>
          <span
            className="confidence-badge"
            style={confidenceStyle[report.confidence]}
          >
            {report.confidence} Confidence
          </span>
        </div>
        <p className="reason">{report.summary}</p>
      </section>

      {/* Root Causes */}
      <section>
        <h2>Root Causes</h2>
        <div className="table-wrapper">
          <table className="dlp-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Rule</th>
                <th>Issue</th>
                <th>Impact</th>
              </tr>
            </thead>
            <tbody>
              {report.root_causes.map((rc, i) => (
                <RootCauseRow key={i} rc={rc} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Event Trend */}
      <section>
        <h2>Daily Event Trend</h2>
        <div className="trend-chart">
          {report.event_trend.map((d) => {
            const max = Math.max(...report.event_trend.map((e) => e.count));
            const pct = (d.count / max) * 100;
            return (
              <div key={d.date} className="trend-bar-row">
                <span className="trend-label">{d.date.slice(5)}</span>
                <div className="trend-bar-track">
                  <div
                    className="trend-bar-fill"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="trend-count">{d.count}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Evidence */}
      <section>
        <h2>Evidence</h2>
        <EvidencePanel title="📄 Configuration" items={report.evidence.config} />
        <EvidencePanel title="📊 Logs" items={report.evidence.logs} />
        <EvidencePanel title="💻 Code" items={report.evidence.code} />
      </section>

      {/* Recommendations */}
      <section>
        <h2>Recommendations</h2>
        <div className="cards-grid">
          {report.recommendations.map((rec) => (
            <div key={rec.priority} className="card">
              <div className="card-header">
                <h3>
                  {severityIcon[rec.severity]} #{rec.priority} — {rec.title}
                </h3>
              </div>
              <p className="reason">{rec.description}</p>
              {rec.action && (
                <pre className="evidence-code">
                  <code>{rec.action}</code>
                </pre>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Unknowns */}
      {report.unknowns.length > 0 && (
        <section>
          <h2>Unknowns &amp; Next Steps</h2>
          <ul className="unknowns-list">
            {report.unknowns.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Download */}
      <button className="download-btn" disabled title="Coming soon">
        📥 Download as Word
      </button>
    </div>
  );
}

function RootCauseRow({ rc }: { rc: DlpDiagnosticsResponse["root_causes"][number] }) {
  const [expanded, setExpanded] = useState(false);
  const hasPreds = rc.predicates && rc.predicates.length > 0;
  return (
    <>
      <tr
        className={`severity-${rc.severity}${hasPreds ? " expandable" : ""}`}
        onClick={() => hasPreds && setExpanded(!expanded)}
        style={hasPreds ? { cursor: "pointer" } : undefined}
      >
        <td>{severityIcon[rc.severity]} {rc.severity}</td>
        <td className="col-name">
          {hasPreds && <span className="expand-icon">{expanded ? "▾" : "▸"}</span>}
          {rc.rule}
        </td>
        <td>{rc.issue}</td>
        <td>{rc.impact}</td>
      </tr>
      {expanded && hasPreds && (
        <tr className="predicates-row">
          <td colSpan={4}>
            <div className="predicates-detail">
              <strong>Predicates / Conditions on this rule:</strong>
              <ul>
                {rc.predicates.map((p, j) => (
                  <li key={j}><code>{p}</code></li>
                ))}
              </ul>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function EvidencePanel({ title, items }: { title: string; items: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="evidence-section">
      <button
        className="evidence-toggle"
        onClick={() => setOpen(!open)}
        type="button"
      >
        {open ? "▾" : "▸"} {title} ({items.length})
      </button>
      {open && (
        <ul className="evidence-list">
          {items.map((item, i) => (
            <li key={i}>
              <code>{item}</code>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
