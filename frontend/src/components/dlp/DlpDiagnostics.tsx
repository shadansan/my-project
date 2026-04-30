import { useState, type FormEvent } from "react";
import {
  runDlpDiagnostics,
  type DlpDiagnosticsRequest,
  type DlpDiagnosticsResponse,
} from "../../api/client";
import DlpReport from "./DlpReport";

const STEPS = [
  "Extracting configuration...",
  "Querying Kusto logs...",
  "Searching source code...",
  "Correlating findings...",
  "Generating report...",
];

const GUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const WORKLOADS = ["Exchange", "SharePoint", "Teams", "OneDrive", "Endpoint"];

export default function DlpDiagnostics() {
  const [tenantId, setTenantId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [problemDescription, setProblemDescription] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [workload, setWorkload] = useState("");
  const [policyName, setPolicyName] = useState("");
  const [showOptional, setShowOptional] = useState(false);

  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<DlpDiagnosticsResponse | null>(null);

  const valid = GUID_RE.test(tenantId) && file !== null && problemDescription.trim().length > 0;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!valid || !file) return;

    setLoading(true);
    setError(null);
    setReport(null);
    setCurrentStep(0);

    // Simulate step progression while the API call runs
    const stepTimers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 1; i < STEPS.length; i++) {
      stepTimers.push(setTimeout(() => setCurrentStep(i), i * 600));
    }

    try {
      const req: DlpDiagnosticsRequest = {
        tenantId,
        problemDescription,
        ...(timeframe && { timeframe }),
        ...(workload && { workload }),
        ...(policyName && { policyName }),
      };
      const data = await runDlpDiagnostics(req, file);
      // Wait for step animation to finish before showing report
      await new Promise((r) => setTimeout(r, STEPS.length * 600));
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred";
      setError(msg);
    } finally {
      stepTimers.forEach(clearTimeout);
      setLoading(false);
    }
  };

  return (
    <>
      <header>
        <h1>DLP Diagnostics</h1>
        <p>Diagnose M365 Data Loss Prevention policy issues</p>
      </header>

      <main>
        <form className="dlp-form" onSubmit={handleSubmit}>
          <h2>📋 Diagnostic Input</h2>

          {/* Tenant ID */}
          <label className="dlp-label" htmlFor="tenantId">
            Tenant ID
          </label>
          <input
            id="tenantId"
            className="dlp-input"
            type="text"
            placeholder="e.g., 72f988bf-86f1-41af-91ab-2d7cd011db47"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
          />
          {tenantId && !GUID_RE.test(tenantId) && (
            <span className="field-error">Must be a valid GUID</span>
          )}

          {/* File upload */}
          <div className="file-upload">
            <label htmlFor="dlpFile">DLP Export ZIP</label>
            <input
              id="dlpFile"
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && <span className="file-name">{file.name}</span>}
          </div>

          {/* Problem description */}
          <label className="dlp-label" htmlFor="problemDesc">
            Problem Description
          </label>
          <textarea
            id="problemDesc"
            rows={4}
            placeholder="Describe what's going wrong, e.g., 'false positives on Credit Card detection in Teams'"
            value={problemDescription}
            onChange={(e) => setProblemDescription(e.target.value)}
          />

          {/* Optional fields (collapsible) */}
          <button
            type="button"
            className="toggle-optional"
            onClick={() => setShowOptional(!showOptional)}
          >
            {showOptional ? "▾" : "▸"} Optional Fields
          </button>

          {showOptional && (
            <div className="optional-fields">
              <label className="dlp-label" htmlFor="timeframe">
                Timeframe
              </label>
              <input
                id="timeframe"
                className="dlp-input"
                type="text"
                placeholder="e.g., Last 14 days"
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
              />

              <label className="dlp-label" htmlFor="workload">
                Affected Workload
              </label>
              <select
                id="workload"
                className="dlp-input"
                value={workload}
                onChange={(e) => setWorkload(e.target.value)}
              >
                <option value="">— Select —</option>
                {WORKLOADS.map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </select>

              <label className="dlp-label" htmlFor="policyName">
                Policy / Rule Name
              </label>
              <input
                id="policyName"
                className="dlp-input"
                type="text"
                placeholder="e.g., M365 DLP - Credit Card Protection"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
              />
            </div>
          )}

          <button type="submit" disabled={!valid || loading}>
            {loading ? "Running…" : "Run Diagnostics"}
          </button>
        </form>

        {/* Loading steps */}
        {loading && (
          <div className="step-indicators">
            {STEPS.map((step, i) => (
              <div
                key={i}
                className={`step-indicator ${i < currentStep ? "done" : i === currentStep ? "active" : ""}`}
              >
                <span className="step-icon">
                  {i < currentStep ? "✅" : i === currentStep ? "⏳" : "⬜"}
                </span>
                {step}
              </div>
            ))}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {report && <DlpReport report={report} />}
      </main>
    </>
  );
}
