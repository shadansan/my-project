import { useState } from "react";
import "./FileActivityTimeline.css";

/* ── Types ── */

export interface SensitiveInfoType {
  type: string;
  count: number;
  confidence: number;
}

export interface DlpPolicyMatch {
  policyName: string;
  priority: number;
  rulesMatched: number;
  policyEnabled: boolean;
  mode: string;
  lastModifiedUtc: string;
}

export interface FileActivity {
  operation: string;
  creationTimeUtc: string;
  enforcementMode: "Block" | "Audit";
  actionsPerformed: string;
  policyMatched: string;
  ruleMatched: string;
}

export interface FileActivityData {
  deviceName: string;
  fileFullPath: string;
  lastActivityBy: string;
  dateRangeStart: string;
  dateRangeEnd: string;
  sensitiveInfoTypes: SensitiveInfoType[];
  dlpPolicies: DlpPolicyMatch[];
  activities: FileActivity[];
}

/**
 * A unified timeline event — can be a file activity, SIT detection, or policy change.
 */
type TimelineEventKind = "activity" | "sit-detected" | "policy-change" | "file-start";

interface TimelineEvent {
  kind: TimelineEventKind;
  timestamp: string;
  // activity fields
  activity?: FileActivity;
  // SIT fields
  sits?: SensitiveInfoType[];
  // policy fields
  policy?: DlpPolicyMatch;
}

/* ── Helpers ── */

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) +
    " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function getOperationIcon(operation: string): string {
  if (operation.includes("Upload") || operation.includes("Cloud")) return "☁️";
  if (operation.includes("Clipboard")) return "📋";
  if (operation.includes("Network") || operation.includes("Share")) return "🌐";
  if (operation.includes("Print")) return "🖨️";
  if (operation.includes("USB") || operation.includes("Removable")) return "💾";
  return "📄";
}

function getOperationLabel(operation: string): string {
  return operation
    .replace(/([A-Z])/g, " $1")
    .replace(/^ /, "")
    .replace(/ To /g, " to ")
    .replace(/ From /g, " from ");
}

/** Build a unified timeline from all data sources */
function buildTimeline(data: FileActivityData): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  // File start event (beginning of observation)
  events.push({
    kind: "file-start",
    timestamp: data.dateRangeStart,
  });

  // SIT detection — placed right after file start
  if (data.sensitiveInfoTypes.length > 0) {
    events.push({
      kind: "sit-detected",
      timestamp: data.dateRangeStart,
      sits: data.sensitiveInfoTypes,
    });
  }

  // Policy changes
  for (const pol of data.dlpPolicies) {
    events.push({
      kind: "policy-change",
      timestamp: pol.lastModifiedUtc,
      policy: pol,
    });
  }

  // File activities
  for (const act of data.activities) {
    events.push({
      kind: "activity",
      timestamp: act.creationTimeUtc,
      activity: act,
    });
  }

  // Sort chronologically
  events.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  return events;
}

/* ── Component ── */

interface Props {
  data: FileActivityData;
}

export default function FileActivityTimeline({ data }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<Set<number>>(new Set());
  const timeline = buildTimeline(data);

  const toggle = (idx: number) => {
    setExpandedIdx((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const blockCount = data.activities.filter((a) => a.enforcementMode === "Block").length;
  const auditCount = data.activities.filter((a) => a.enforcementMode === "Audit").length;

  return (
    <div className="tl-container">
      {/* ── File identity card ── */}
      <div className="tl-file-card">
        <div className="tl-file-icon">📄</div>
        <div className="tl-file-info">
          <h2 className="tl-file-name">{data.fileFullPath.split("\\").pop()}</h2>
          <code className="tl-file-path">{data.fileFullPath}</code>
          <div className="tl-file-meta">
            <span>🖥️ {data.deviceName}</span>
            <span>👤 {data.lastActivityBy}</span>
          </div>
        </div>
      </div>

      {/* ── Time range bar ── */}
      <div className="tl-range-bar">
        <span className="tl-range-start">{formatDateTime(data.dateRangeStart)}</span>
        <div className="tl-range-line">
          <div className="tl-range-stats">
            <span className="tl-range-stat">{data.activities.length} events</span>
            <span className="tl-range-stat tl-stat-block">⛔ {blockCount} blocked</span>
            <span className="tl-range-stat tl-stat-audit">👁️ {auditCount} audited</span>
          </div>
        </div>
        <span className="tl-range-end">{formatDateTime(data.dateRangeEnd)}</span>
      </div>

      {/* ── Vertical Timeline ── */}
      <div className="tl-vertical">
        {timeline.map((event, idx) => (
          <div
            key={idx}
            className={`tl-node tl-node-${event.kind}${expandedIdx.has(idx) ? " expanded" : ""}`}
            onClick={() => (event.kind === "activity" ? toggle(idx) : undefined)}
          >
            {/* The connector line + dot */}
            <div className="tl-spine">
              <div className="tl-dot" />
            </div>

            {/* Event card */}
            <div className="tl-card">
              <span className="tl-timestamp">{formatTime(event.timestamp)}</span>

              {event.kind === "file-start" && (
                <div className="tl-event-body">
                  <div className="tl-event-title">
                    <span className="tl-icon">📂</span>
                    <strong>File Activity Monitoring Started</strong>
                  </div>
                  <p className="tl-event-desc">
                    Tracking began on <strong>{data.fileFullPath.split("\\").pop()}</strong>
                  </p>
                </div>
              )}

              {event.kind === "sit-detected" && event.sits && (
                <div className="tl-event-body">
                  <div className="tl-event-title">
                    <span className="tl-icon">🔐</span>
                    <strong>Sensitive Information Detected</strong>
                    <span className="tl-badge tl-badge-sit">{event.sits.length} types</span>
                  </div>
                  <div className="tl-sit-grid">
                    {event.sits.map((sit) => (
                      <div key={sit.type} className="tl-sit-row">
                        <span className="tl-sit-name">{sit.type}</span>
                        <span className="tl-sit-count">{sit.count}×</span>
                        <span className={`tl-confidence ${sit.confidence >= 90 ? "high" : sit.confidence >= 70 ? "med" : "low"}`}>
                          {sit.confidence}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {event.kind === "policy-change" && event.policy && (
                <div className="tl-event-body">
                  <div className="tl-event-title">
                    <span className="tl-icon">🛡️</span>
                    <strong>Policy Applied</strong>
                    <span className={`tl-badge ${event.policy.mode === "Enable" ? "tl-badge-active" : "tl-badge-inactive"}`}>
                      {event.policy.mode}
                    </span>
                  </div>
                  <div className="tl-policy-detail">
                    <span className="tl-policy-name">{event.policy.policyName}</span>
                    <div className="tl-policy-meta">
                      <span>Priority: {event.policy.priority}</span>
                      <span>Rules matched: {event.policy.rulesMatched}</span>
                    </div>
                  </div>
                </div>
              )}

              {event.kind === "activity" && event.activity && (
                <div className="tl-event-body">
                  <div className="tl-event-title">
                    <span className="tl-icon">{getOperationIcon(event.activity.operation)}</span>
                    <strong>{getOperationLabel(event.activity.operation)}</strong>
                    <span className={`tl-badge ${event.activity.enforcementMode === "Block" ? "tl-badge-block" : "tl-badge-audit"}`}>
                      {event.activity.enforcementMode === "Block" ? "⛔ Blocked" : "👁️ Audit"}
                    </span>
                  </div>

                  {expandedIdx.has(idx) && (
                    <div className="tl-activity-details">
                      <div className="tl-detail-row">
                        <span className="tl-detail-label">Action Taken</span>
                        <span className="tl-detail-value">{event.activity.actionsPerformed}</span>
                      </div>
                      <div className="tl-detail-row">
                        <span className="tl-detail-label">Policy Matched</span>
                        <span className="tl-detail-value">{event.activity.policyMatched}</span>
                      </div>
                      <div className="tl-detail-row">
                        <span className="tl-detail-label">Rule Matched</span>
                        <span className="tl-detail-value">{event.activity.ruleMatched}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* End marker */}
        <div className="tl-node tl-node-end">
          <div className="tl-spine">
            <div className="tl-dot" />
          </div>
          <div className="tl-card">
            <span className="tl-timestamp">{formatTime(data.dateRangeEnd)}</span>
            <div className="tl-event-body">
              <div className="tl-event-title">
                <span className="tl-icon">🏁</span>
                <strong>End of Observation Window</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
