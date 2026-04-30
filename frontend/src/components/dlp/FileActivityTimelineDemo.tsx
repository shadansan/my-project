import FileActivityTimeline, { type FileActivityData } from "./FileActivityTimeline";

/** Sample data matching the screenshot for demonstration */
const SAMPLE_DATA: FileActivityData = {
  deviceName: "desktop-4fi2d7s",
  fileFullPath: "C:\\Users\\Pramila\\Test Files\\SIT Test.docx",
  lastActivityBy: "EUCopilot@MultiCloudTenant01.onmicrosoft.com",
  dateRangeStart: "2026-04-22T05:58:59Z",
  dateRangeEnd: "2026-04-22T08:03:58Z",
  sensitiveInfoTypes: [
    { type: "EU Driver's License Number", count: 3, confidence: 99 },
    { type: "EU Passport Number", count: 5, confidence: 99 },
    { type: "Credit Card Number", count: 1, confidence: 85 },
  ],
  dlpPolicies: [
    {
      policyName: "Custom policy for SITs",
      priority: 59,
      rulesMatched: 1,
      policyEnabled: true,
      mode: "Enable",
      lastModifiedUtc: "2026-04-22T08:02:49Z",
    },
  ],
  activities: [
    { operation: "FileCopiedToNetworkShare", creationTimeUtc: "2026-04-22T05:58:59Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileUploadedToCloud", creationTimeUtc: "2026-04-22T05:59:19Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileUploadedToCloud", creationTimeUtc: "2026-04-22T06:16:44Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T06:16:55Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T06:16:59Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T06:17:17Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileUploadedToCloud", creationTimeUtc: "2026-04-22T06:25:11Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileUploadedToCloud", creationTimeUtc: "2026-04-22T07:23:37Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T07:25:19Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T07:25:22Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T07:45:08Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileCopiedToClipboard", creationTimeUtc: "2026-04-22T07:45:58Z", enforcementMode: "Audit", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
    { operation: "FileUploadedToCloud", creationTimeUtc: "2026-04-22T08:03:58Z", enforcementMode: "Block", actionsPerformed: "GenerateAlert", policyMatched: "Custom policy for SITs", ruleMatched: "Test SIT" },
  ],
};

export default function FileActivityTimelineDemo() {
  return (
    <>
      <header>
        <h1>File Activity Timeline</h1>
        <p>Visual chronological view of DLP file events</p>
      </header>
      <main>
        <FileActivityTimeline data={SAMPLE_DATA} />
      </main>
    </>
  );
}
