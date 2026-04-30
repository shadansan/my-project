"""
DLP Diagnostics Service — real implementation.

Workflow:
  1. Extract and parse DLP config from an uploaded ZIP (CLIXML format)
  2. Analyse the config for false-positive patterns
  3. Query Kusto logs via ``az rest``
  4. Generate code-level evidence references
  5. Produce targeted recommendations
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import logging

import logging

_logger = logging.getLogger("dlp_diagnostics")

from models.schemas import (
    DlpDiagnosticsResponse,
    DlpEvidence,
    DlpRecommendation,
    DlpRootCause,
)

# ---------------------------------------------------------------------------
# XML / CLIXML helpers
# ---------------------------------------------------------------------------

NS = {"ps": "http://schemas.microsoft.com/powershell/2004/04"}

_TENANT_RE = re.compile(r"^[0-9a-fA-F\-]{36}$")


def _sanitize_tenant(tid: str) -> str:
    tid = tid.strip()
    if not _TENANT_RE.match(tid):
        raise ValueError(f"Invalid tenant_id format: {tid!r}")
    return tid


def _get_str(props: ET.Element, name: str) -> str | None:
    el = props.find(f'ps:S[@N="{name}"]', NS)
    return el.text if el is not None and el.text else None


def _get_bool(props: ET.Element, name: str) -> bool | None:
    el = props.find(f'ps:B[@N="{name}"]', NS)
    if el is None or el.text is None:
        return None
    return el.text.lower() == "true"


def _get_int(props: ET.Element, name: str) -> int | None:
    el = props.find(f'ps:I32[@N="{name}"]', NS)
    if el is None or el.text is None:
        return None
    try:
        return int(el.text)
    except ValueError:
        return None


def _get_tostring(props: ET.Element, name: str) -> str | None:
    obj = props.find(f'ps:Obj[@N="{name}"]', NS)
    if obj is None:
        return None
    ts = obj.find("ps:ToString", NS)
    return ts.text if ts is not None else None


def _get_lst_strings(props: ET.Element, name: str) -> list[str]:
    lst = props.find(f'ps:Obj[@N="{name}"]/ps:LST', NS)
    if lst is None:
        return []
    return [s.text for s in lst if s.text]


# ---------------------------------------------------------------------------
# Step 1 — Extract & parse DLP config from ZIP
# ---------------------------------------------------------------------------

def _parse_zip(zip_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Return (policies, rules) parsed from DLP.xml inside the ZIP."""
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    xml_name = next((n for n in names if n.lower().endswith(".xml")), None)
    if xml_name is None:
        raise ValueError("ZIP does not contain an XML file")

    text = zf.read(xml_name).decode("utf-8-sig", errors="replace")
    root = ET.fromstring(text)

    top_props = root.find('.//ps:Obj[@RefId="0"]/ps:Props', NS)
    if top_props is None:
        raise ValueError("Cannot find top-level Props in CLIXML")

    policies = _parse_policies(top_props)
    rules = _parse_rules(top_props)
    return policies, rules


def _parse_policies(top_props: ET.Element) -> list[dict]:
    lst = top_props.find('ps:Obj[@N="DlpCompliancePolicies"]/ps:LST', NS)
    if lst is None:
        return []
    policies: list[dict] = []
    for obj in lst:
        props = obj.find("ps:Props", NS)
        if props is None:
            continue
        pol: dict[str, Any] = {
            "DisplayName": _get_str(props, "DisplayName") or _get_str(props, "Name") or "Unknown",
            "Mode": _get_tostring(props, "Mode") or "Unknown",
            "Workload": _get_tostring(props, "Workload") or "",
            "Enabled": _get_bool(props, "Enabled"),
            "Priority": _get_int(props, "Priority"),
            "DistributionStatus": _get_tostring(props, "DistributionStatus") or "",
        }
        # Location bindings
        for loc_name in (
            "ExchangeLocation", "SharePointLocation", "OneDriveLocation",
            "TeamsLocation", "EndpointDlpLocation",
        ):
            items = props.find(f'ps:Obj[@N="{loc_name}"]/ps:LST', NS)
            pol[loc_name] = len(items) if items is not None else 0
        policies.append(pol)
    return policies


def _parse_rules(top_props: ET.Element) -> list[dict]:
    lst = top_props.find('ps:Obj[@N="DlpComplianceRules"]/ps:LST', NS)
    if lst is None:
        return []
    rules: list[dict] = []
    for obj in lst:
        props = obj.find("ps:Props", NS)
        if props is None:
            continue
        rule: dict[str, Any] = {
            "DisplayName": _get_str(props, "DisplayName") or _get_str(props, "Name") or "Unknown",
            "ParentPolicyName": _get_str(props, "ParentPolicyName") or "",
            "BlockAccess": _get_bool(props, "BlockAccess") or False,
            "Disabled": _get_bool(props, "Disabled") or False,
            "Priority": _get_int(props, "Priority"),
            "DocumentIsUnsupported": _get_bool(props, "DocumentIsUnsupported") or False,
            "ProcessingLimitExceeded": _get_bool(props, "ProcessingLimitExceeded") or False,
            "ContentExtensionMatchesWords": _get_lst_strings(props, "ContentExtensionMatchesWords"),
            "MessageTypeMatches": _get_tostring(props, "MessageTypeMatches"),
        }

        # Parse AdvancedRule JSON
        ar_text = _get_str(props, "AdvancedRule")
        rule["AdvancedRule"] = None
        rule["SensitiveTypes"] = []
        rule["Conditions"] = []
        if ar_text:
            cleaned = ar_text.replace("_x000D__x000A_", "\n")
            try:
                ar_json = json.loads(cleaned)
                rule["AdvancedRule"] = ar_json
                _extract_conditions(ar_json.get("Condition", {}), rule)
            except json.JSONDecodeError:
                pass

        # Also check legacy ContentContainsSensitiveInformation field
        ccsi = _get_str(props, "ContentContainsSensitiveInformation")
        if ccsi and not rule["SensitiveTypes"]:
            try:
                parsed = json.loads(ccsi)
                if isinstance(parsed, list):
                    for group_set in parsed:
                        for grp in group_set.get("Groups", []):
                            rule["SensitiveTypes"].extend(grp.get("Sensitivetypes", []))
            except (json.JSONDecodeError, TypeError):
                pass

        rules.append(rule)
    return rules


def _extract_conditions(condition: dict, rule: dict) -> None:
    """Recursively walk the AdvancedRule condition tree."""
    cond_name = condition.get("ConditionName")
    if cond_name:
        rule["Conditions"].append(cond_name)
        if cond_name == "ContentContainsSensitiveInformation":
            value = condition.get("Value", [])
            if isinstance(value, list):
                for group_set in value:
                    if isinstance(group_set, dict):
                        for grp in group_set.get("Groups", []):
                            rule["SensitiveTypes"].extend(grp.get("Sensitivetypes", []))
        elif cond_name == "ContentExtensionMatchesWords":
            value = condition.get("Value", [])
            if isinstance(value, list) and not rule["ContentExtensionMatchesWords"]:
                rule["ContentExtensionMatchesWords"] = value
        elif cond_name == "MessageTypeMatches":
            rule["MessageTypeMatches"] = condition.get("Value", "")
        elif cond_name == "DocumentIsUnsupported":
            rule["DocumentIsUnsupported"] = bool(condition.get("Value"))
        elif cond_name == "ProcessingLimitExceeded":
            rule["ProcessingLimitExceeded"] = bool(condition.get("Value"))

    for sub in condition.get("SubConditions", []):
        _extract_conditions(sub, rule)


# ---------------------------------------------------------------------------
# Step 2 — Analyse config for false-positive patterns
# ---------------------------------------------------------------------------

_HIGH_RISK_SITS = {"credit card", "social security", "ssn"}


def _describe_predicates(rule: dict) -> list[str]:
    """Build a human-readable list of all predicates/conditions on a rule."""
    preds: list[str] = []

    for sit in rule.get("SensitiveTypes", []):
        name = sit.get("Name", "Unknown SIT")
        minconf = sit.get("Minconfidence", "?")
        maxconf = sit.get("Maxconfidence", "?")
        mincount = sit.get("Mincount", "?")
        conf_level = sit.get("Confidencelevel", "")
        label = f"ContentContainsSensitiveInformation: '{name}'"
        details = []
        if conf_level:
            details.append(f"level={conf_level}")
        details.append(f"minConfidence={minconf}")
        if maxconf and maxconf != "?":
            details.append(f"maxConfidence={maxconf}")
        details.append(f"minCount={mincount}")
        preds.append(f"{label} ({', '.join(details)})")

    ext_words = rule.get("ContentExtensionMatchesWords", [])
    if ext_words:
        preds.append(f"ContentExtensionMatchesWords: {ext_words}")

    msg_type = rule.get("MessageTypeMatches")
    if msg_type:
        preds.append(f"MessageTypeMatches: '{msg_type}'")

    if rule.get("DocumentIsUnsupported"):
        preds.append("DocumentIsUnsupported: True")

    if rule.get("ProcessingLimitExceeded"):
        preds.append("ProcessingLimitExceeded: True")

    if rule.get("BlockAccess"):
        preds.append("Action: BlockAccess")
    else:
        preds.append("Action: Audit / Notify")

    # Add any other raw conditions we found
    for cond in rule.get("Conditions", []):
        if cond not in ("ContentContainsSensitiveInformation",
                        "ContentExtensionMatchesWords",
                        "MessageTypeMatches",
                        "DocumentIsUnsupported",
                        "ProcessingLimitExceeded"):
            preds.append(f"Condition: {cond}")

    if not preds or (len(preds) == 1 and preds[0].startswith("Action:")):
        preds.insert(0, "(no content conditions detected)")

    return preds


def _analyse_config(
    policies: list[dict],
    rules: list[dict],
) -> tuple[list[DlpRootCause], list[str], list[str]]:
    """Return (root_causes, config_evidence, unknowns)."""
    root_causes: list[DlpRootCause] = []
    evidence: list[str] = []
    unknowns: list[str] = []

    # --- Policy-level checks ---
    for pol in policies:
        name = pol["DisplayName"]
        mode = pol["Mode"]
        enabled = pol.get("Enabled")
        dist = pol.get("DistributionStatus", "")

        evidence.append(
            f"Policy '{name}': Mode={mode}, Workload={pol.get('Workload','')}, "
            f"Enabled={enabled}, DistributionStatus={dist}"
        )

        if enabled is False:
            root_causes.append(DlpRootCause(
                rule=name,
                issue="Policy is disabled",
                impact="No DLP enforcement from this policy",
                severity="info",
            ))

        if dist and dist.lower() not in ("success", ""):
            root_causes.append(DlpRootCause(
                rule=name,
                issue=f"DistributionStatus is '{dist}' (not Success)",
                impact="Policy may not be fully deployed to all workloads",
                severity="warning",
            ))

        if mode and mode.lower().startswith("test"):
            evidence.append(f"  → Policy '{name}' is in test/simulation mode ({mode})")

    # --- Rule-level checks ---
    for rule in rules:
        rname = rule["DisplayName"]
        parent = rule["ParentPolicyName"]
        preds = _describe_predicates(rule)

        # Add predicate summary to evidence for every rule
        evidence.append(
            f"Rule '{rname}' (policy '{parent}'): predicates = {' | '.join(preds)}"
        )

        if rule["Disabled"]:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue="Rule is disabled",
                impact="No enforcement from this rule",
                severity="info",
                predicates=preds,
            ))

        sits: list[dict] = rule.get("SensitiveTypes", [])
        conditions: list[str] = rule.get("Conditions", [])
        has_sit = bool(sits) or "ContentContainsSensitiveInformation" in conditions
        block = rule["BlockAccess"]
        ext_words = rule.get("ContentExtensionMatchesWords", [])
        msg_type = rule.get("MessageTypeMatches")
        doc_unsup = rule.get("DocumentIsUnsupported", False)
        proc_limit = rule.get("ProcessingLimitExceeded", False)

        # SIT confidence checks
        for sit in sits:
            sit_name = sit.get("Name", "Unknown SIT")
            minconf = sit.get("Minconfidence")
            maxconf = sit.get("Maxconfidence")
            mincount = sit.get("Mincount")
            conf_level = sit.get("Confidencelevel", "")

            evidence.append(
                f"Rule '{rname}' (policy '{parent}'): SIT '{sit_name}' — "
                f"Confidencelevel={conf_level}, Minconfidence={minconf}, "
                f"Maxconfidence={maxconf}, Mincount={mincount}"
            )

            is_high_risk = any(hr in sit_name.lower() for hr in _HIGH_RISK_SITS)

            if minconf is not None and minconf < 75:
                root_causes.append(DlpRootCause(
                    rule=rname,
                    issue=(
                        f"SIT '{sit_name}' has Minconfidence={minconf} (<75) — "
                        f"this will match on regex alone without corroborative evidence"
                    ),
                    impact=(
                        f"High false-positive rate"
                        + (" — especially risky for " + sit_name if is_high_risk else "")
                    ),
                    severity="critical",
                    predicates=preds,
                ))
            elif minconf is not None and minconf < 85:
                root_causes.append(DlpRootCause(
                    rule=rname,
                    issue=f"SIT '{sit_name}' has Minconfidence={minconf} (<85)",
                    impact="Moderate false-positive risk with limited corroborative evidence",
                    severity="warning",
                    predicates=preds,
                ))

            if mincount is not None and mincount == 1:
                root_causes.append(DlpRootCause(
                    rule=rname,
                    issue=f"SIT '{sit_name}' has Mincount=1 — single instance triggers match",
                    impact="Even one accidental pattern match will fire the rule",
                    severity="warning" if (minconf and minconf >= 75) else "info",
                    predicates=preds,
                ))

        # Extension-only block
        if ext_words and block and not has_sit:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue=(
                    f"ContentExtensionMatchesWords={ext_words} with BlockAccess=true "
                    f"and NO SIT condition"
                ),
                impact="Blocks ALL files of the specified type regardless of content",
                severity="critical",
                predicates=preds,
            ))

        # MessageTypeMatches without SIT
        if msg_type and not has_sit:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue=f"MessageTypeMatches='{msg_type}' with no SIT condition",
                impact="Matches all messages of this type regardless of sensitive content",
                severity="warning",
                predicates=preds,
            ))

        # DocumentIsUnsupported / ProcessingLimitExceeded
        if doc_unsup:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue="Rule triggers on DocumentIsUnsupported — fires for unscannable files",
                impact="Generates noise for password-protected, encrypted, or corrupt files",
                severity="info",
                predicates=preds,
            ))
        if proc_limit:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue="Rule triggers on ProcessingLimitExceeded — fires when scan times out",
                impact="Generates noise for very large files or slow processing",
                severity="info",
                predicates=preds,
            ))

        # No real conditions at all
        if not conditions and not sits and not ext_words and not msg_type and not doc_unsup and not proc_limit:
            root_causes.append(DlpRootCause(
                rule=rname,
                issue="Rule has no detectable conditions",
                impact="Rule may match all content or be misconfigured",
                severity="critical",
                predicates=preds,
            ))

    return root_causes, evidence, unknowns


# ---------------------------------------------------------------------------
# Step 3 — Query Kusto
# ---------------------------------------------------------------------------

_KUSTO_UNREACHABLE = None  # sentinel: None means unreachable, [] means reachable but empty


def _query_kusto(database: str, kql: str) -> list[dict] | None:
    """Execute a KQL query against the Kusto cluster via ``az rest``.

    Returns a list of row-dicts on success (may be empty), or ``None`` if the
    cluster is unreachable / auth failed.
    """
    body = json.dumps({"db": database, "csl": kql})
    fd, body_file = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        cmd = (
            f'az rest --method post'
            f' --url "https://o365monwus.westus.kusto.windows.net/v1/rest/query"'
            f' --body "@{body_file}"'
            f' --resource "https://o365monwus.westus.kusto.windows.net"'
            f' --headers "Content-Type=application/json"'
            f' -o json'
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )
        if result.returncode != 0:
            stderr = result.stderr or ""
            # Distinguish real unreachability from bad queries
            if "BadRequest" in stderr or "Semantic error" in stderr:
                _logger.warning("Kusto query error (bad KQL): %s", stderr[:300])
                # Return empty — cluster is reachable, query is just invalid
                return []
            _logger.warning("Kusto query failed (rc=%d): %s", result.returncode, stderr[:500])
            return _KUSTO_UNREACHABLE
        data = json.loads(result.stdout)
        columns = [c["ColumnName"] for c in data["Tables"][0]["Columns"]]
        rows = data["Tables"][0]["Rows"]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as exc:
        _logger.warning("Kusto query exception: %s", exc)
        return _KUSTO_UNREACHABLE
    finally:
        try:
            os.unlink(body_file)
        except OSError:
            pass


def _run_kusto_queries(
    tenant_id: str,
    workload: str | None = None,
    timeframe: str | None = None,
) -> tuple[list[str], list[dict], list[str]]:
    """Run all Kusto queries in parallel.  Returns (log_evidence, trend_data, unknowns)."""
    tid = _sanitize_tenant(tenant_id)
    db = "o365monitoring"

    # Build optional KQL filter fragments
    time_filter = "30d"  # default
    if timeframe:
        tf = timeframe.strip().lower()
        if "7" in tf or "week" in tf:
            time_filter = "7d"
        elif "14" in tf or "2 week" in tf:
            time_filter = "14d"
        elif "90" in tf or "quarter" in tf:
            time_filter = "90d"

    wl_clause = ""
    if workload:
        wl_safe = workload.strip().replace('"', '\\"')
        # DIPolicyAgentEvent may not have a 'Workload' column; filter via
        # AdditionalData (JSON string field) which typically contains workload info
        wl_clause = f'| where AdditionalData contains "{wl_safe}" '

    queries = {
        "event_summary": (
            f'DIPolicyAgentEvent | where TenantId == "{tid}" '
            f'| where env_time > ago({time_filter}) '
            f'{wl_clause}'
            f'| summarize count() by AlertType, RuleId '
            f'| order by count_ desc | take 30'
        ),
        "daily_trend": (
            f'DIPolicyAgentEvent | where TenantId == "{tid}" '
            f'| where env_time > ago({time_filter}) '
            f'{wl_clause}'
            f'| summarize count() by bin(env_time, 1d) '
            f'| order by env_time asc'
        ),
        "errors": (
            f'DIPolicyAgentEvent | where TenantId == "{tid}" '
            f'| where env_time > ago({time_filter}) | where Error != "" '
            f'{wl_clause}'
            f'| summarize count() by Error '
            f'| order by count_ desc | take 20'
        ),
        "recent_alerts": (
            f'DIPolicyAgentEvent | where TenantId == "{tid}" '
            f'| where env_time > ago({time_filter}) | where AlertType == "Custom" '
            f'{wl_clause}'
            f'| project env_time, AlertType, RuleId, TemplateType, AdditionalData '
            f'| top 5 by env_time desc'
        ),
    }

    results: dict[str, list[dict] | None] = {}
    kusto_reachable = True

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_query_kusto, db, kql): name
            for name, kql in queries.items()
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception:
                results[name] = _KUSTO_UNREACHABLE

    # Determine reachability: if ALL queries returned None, Kusto is unreachable
    if all(v is None for v in results.values()):
        kusto_reachable = False

    # Build evidence strings
    log_evidence: list[str] = []
    unknowns: list[str] = []

    summary_rows = results.get("event_summary") or []
    if summary_rows:
        total = sum(r.get("count_", 0) for r in summary_rows)
        log_evidence.append(f"Kusto: {total} total DLP events in last 30 days across {len(summary_rows)} AlertType/RuleId combos")
        for r in summary_rows[:10]:
            log_evidence.append(
                f"  AlertType={r.get('AlertType','?')}, RuleId={r.get('RuleId','?')}: {r.get('count_',0)} events"
            )
    elif kusto_reachable:
        log_evidence.append("Kusto: 0 DIPolicyAgentEvent records found for this tenant in the last 30 days")

    error_rows = results.get("errors") or []
    if error_rows:
        log_evidence.append(f"Kusto: {len(error_rows)} distinct error types in last 30 days")
        for r in error_rows[:5]:
            log_evidence.append(f"  Error='{r.get('Error','?')}': {r.get('count_',0)} occurrences")

    recent = results.get("recent_alerts") or []
    if recent:
        log_evidence.append(f"Kusto: {len(recent)} most recent custom alerts sampled")
        for r in recent:
            log_evidence.append(
                f"  {r.get('env_time','?')} AlertType={r.get('AlertType','?')} RuleId={r.get('RuleId','?')}"
            )

    # Trend data
    trend_data = results.get("daily_trend") or []

    if not kusto_reachable:
        unknowns.append(
            "Kusto cluster unreachable — connect to VPN and retry. "
            "Log-based evidence is unavailable for this run."
        )

    return log_evidence, trend_data, unknowns


# ---------------------------------------------------------------------------
# Step 4 — Code-level evidence
# ---------------------------------------------------------------------------

def _generate_code_evidence(rules: list[dict]) -> list[str]:
    """Generate code evidence references based on config findings."""
    evidence: list[str] = []
    has_cc = False
    has_ext_match = False
    has_ssn = False

    for rule in rules:
        for sit in rule.get("SensitiveTypes", []):
            name = sit.get("Name", "").lower()
            if "credit card" in name:
                has_cc = True
            if "social security" in name or "ssn" in name:
                has_ssn = True
        if rule.get("ContentExtensionMatchesWords"):
            has_ext_match = True

    if has_cc:
        evidence.append(
            "Credit Card SIT referenced — see ComplianceFoundation repo: "
            "ExContentContainsSensitiveInformationPredicateTest.cs for SIT evaluation logic"
        )
    if has_ssn:
        evidence.append(
            "SSN SIT referenced — confidence levels affect regex vs corroborative matching. "
            "See ComplianceFoundation repo SIT pattern definitions."
        )
    if has_ext_match:
        evidence.append(
            "ContentExtensionMatchesWords used — see PsDlpComplianceManagementRule.cs "
            "for extension-matching implementation"
        )
    evidence.append(
        "Note: ComplianceFoundation ADO repo may be disabled or access-restricted; "
        "verify permissions if code search fails."
    )
    return evidence


# ---------------------------------------------------------------------------
# Step 5 — Generate recommendations
# ---------------------------------------------------------------------------

def _generate_recommendations(
    root_causes: list[DlpRootCause],
    rules: list[dict],
    tenant_id: str,
    problem_lower: str = "",
) -> list[DlpRecommendation]:
    recs: list[DlpRecommendation] = []
    priority = 0
    seen: set[str] = set()

    # Determine problem focus to boost relevant recommendations
    is_fp = any(kw in problem_lower for kw in ("false positive", "fp", "over-match", "too many match"))
    is_fn = any(kw in problem_lower for kw in ("false negative", "fn", "miss", "not detect", "not catch", "under-match"))
    is_block = any(kw in problem_lower for kw in ("block", "prevent", "cannot send", "cannot share", "can't send"))

    for rc in root_causes:
        key = (rc.severity, rc.issue[:60])
        if key in seen:
            continue
        seen.add(key)

        # Boost severity for findings relevant to the stated problem
        effective_severity = rc.severity
        if is_fp and "Minconfidence" in rc.issue and "low" in rc.issue.lower():
            effective_severity = "critical"
        if is_fp and "no SIT condition" in rc.issue.lower():
            effective_severity = "critical"
        if is_block and "BlockAccess" in rc.issue:
            effective_severity = "critical"

        if "Minconfidence" in rc.issue and effective_severity == "critical":
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="critical",
                title=f"Raise confidence threshold for rule '{rc.rule}'",
                description=(
                    f"{rc.issue}. Increase Minconfidence to at least 85 (High) to require "
                    f"corroborative evidence alongside the regex pattern. This is the single "
                    f"most effective change to reduce false positives."
                ),
                action=(
                    f"Set-DlpComplianceRule -Identity '{rc.rule}' "
                    f"-ContentContainsSensitiveInformation @(@{{Name='<SIT>'; minCount='1'; "
                    f"confidenceLevel='High'}})"
                ),
            ))
        elif "ContentExtensionMatchesWords" in rc.issue and "BlockAccess" in rc.issue:
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="critical",
                title=f"Add SIT condition to extension-based block rule '{rc.rule}'",
                description=(
                    f"{rc.issue}. Add a ContentContainsSensitiveInformation condition so the "
                    f"rule only blocks files that actually contain sensitive data, not every "
                    f"file of that type."
                ),
                action=(
                    f"Set-DlpComplianceRule -Identity '{rc.rule}' "
                    f"-ContentContainsSensitiveInformation @(@{{Name='Credit Card Number'; "
                    f"minCount='1'; confidenceLevel='High'}})"
                ),
            ))
        elif "no detectable conditions" in rc.issue:
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="critical",
                title=f"Add conditions or disable rule '{rc.rule}'",
                description=(
                    f"Rule '{rc.rule}' has no conditions and may match all content. "
                    f"Add appropriate SIT or other conditions, or disable the rule."
                ),
                action=f"Disable-DlpComplianceRule -Identity '{rc.rule}'",
            ))
        elif "Minconfidence" in rc.issue and effective_severity == "warning":
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="warning",
                title=f"Consider raising confidence for rule '{rc.rule}'",
                description=(
                    f"{rc.issue}. A higher confidence threshold (85+) would reduce "
                    f"false positives while maintaining detection of genuine sensitive data."
                ),
            ))
        elif "DocumentIsUnsupported" in rc.issue or "ProcessingLimitExceeded" in rc.issue:
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="info",
                title=f"Switch rule '{rc.rule}' to audit-only mode",
                description=(
                    f"{rc.issue}. Consider running this rule in audit-only (TestWithNotifications) "
                    f"mode to reduce noise while still logging events."
                ),
                action=(
                    f"Set-DlpComplianceRule -Identity '{rc.rule}' "
                    f"-Mode TestWithNotifications"
                ),
            ))
        elif "MessageTypeMatches" in rc.issue:
            priority += 1
            recs.append(DlpRecommendation(
                priority=priority,
                severity="warning",
                title=f"Add SIT condition alongside MessageTypeMatches in '{rc.rule}'",
                description=(
                    f"{rc.issue}. Without a SIT condition, this rule matches "
                    f"all messages of the specified type."
                ),
            ))

    # Always add a monitoring recommendation
    priority += 1
    safe_tid = _sanitize_tenant(tenant_id)
    recs.append(DlpRecommendation(
        priority=priority,
        severity="info",
        title="Monitor DLP event trend after changes",
        description=(
            "After implementing the above changes, monitor the daily event trend "
            "for 7–14 days to verify false positives have decreased."
        ),
        action=(
            f'DIPolicyAgentEvent | where TenantId == "{safe_tid}" '
            f'| where env_time > ago(14d) '
            f'| summarize count() by bin(env_time, 1d) | render timechart'
        ),
    ))

    return recs


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_diagnostics(
    zip_bytes: bytes,
    tenant_id: str,
    problem_description: str,
    timeframe: str | None = None,
    workload: str | None = None,
    policy_name: str | None = None,
) -> DlpDiagnosticsResponse:
    """Execute the full DLP diagnostic workflow and return the response."""
    tenant_id = _sanitize_tenant(tenant_id)
    unknowns: list[str] = []

    # Step 1 — Parse config
    try:
        policies, rules = _parse_zip(zip_bytes)
    except Exception as exc:
        raise ValueError(f"Failed to parse DLP config ZIP: {exc}") from exc

    if not policies and not rules:
        raise ValueError("ZIP contained no DLP policies or rules")

    # Filter to the requested policy/workload scope
    if policy_name:
        pn_lower = policy_name.strip().lower()
        # Try exact match first, then substring match for flexibility
        filtered_policies = [p for p in policies if p["DisplayName"].lower() == pn_lower]
        if not filtered_policies:
            filtered_policies = [p for p in policies if pn_lower in p["DisplayName"].lower()]
        if filtered_policies:
            policies = filtered_policies
            policy_names_set = {p["DisplayName"].lower() for p in policies}
            rules = [r for r in rules if r["ParentPolicyName"].lower() in policy_names_set]
        else:
            raise ValueError(f"Policy '{policy_name}' not found in export")

    if workload:
        wl_lower = workload.strip().lower()
        # Filter policies whose Workload field mentions the selected workload
        policies = [p for p in policies if wl_lower in p.get("Workload", "").lower()]
        # Keep rules belonging to remaining policies
        policy_names = {p["DisplayName"].lower() for p in policies}
        rules = [r for r in rules if r["ParentPolicyName"].lower() in policy_names]

    # Determine problem-type focus for analysis weighting
    problem_lower = problem_description.lower() if problem_description else ""

    # Step 2 — Analyse config
    root_causes, config_evidence, config_unknowns = _analyse_config(policies, rules)
    unknowns.extend(config_unknowns)

    # Step 3 — Query Kusto (best-effort), scoped to workload if specified
    try:
        log_evidence, trend_data, kusto_unknowns = _run_kusto_queries(
            tenant_id, workload=workload, timeframe=timeframe,
        )
        unknowns.extend(kusto_unknowns)
    except Exception:
        log_evidence = []
        trend_data = []
        unknowns.append("Kusto query execution failed — connect to VPN and retry")

    # Step 4 — Code evidence
    code_evidence = _generate_code_evidence(rules)

    # Step 5 — Recommendations (problem-aware)
    recommendations = _generate_recommendations(
        root_causes, rules, tenant_id, problem_lower,
    )

    # Build event trend
    event_trend: list[dict[str, Any]] = []
    for row in trend_data:
        date_val = row.get("env_time", "")
        count_val = row.get("count_", 0)
        if date_val:
            date_str = str(date_val)[:10]
            event_trend.append({"date": date_str, "count": int(count_val)})

    # Build summary
    n_critical = sum(1 for rc in root_causes if rc.severity == "critical")
    n_warning = sum(1 for rc in root_causes if rc.severity == "warning")
    n_info = sum(1 for rc in root_causes if rc.severity == "info")

    scope_parts: list[str] = []
    if policy_name:
        scope_parts.append(f"policy '{policy_name}'")
    if workload:
        scope_parts.append(f"workload '{workload}'")
    scope_desc = f" (scoped to {', '.join(scope_parts)})" if scope_parts else ""

    summary_parts = [
        f"Analyzed {len(policies)} policies and {len(rules)} rules{scope_desc}.",
    ]
    if n_critical:
        summary_parts.append(f"Found {n_critical} critical issue(s).")
    if n_warning:
        summary_parts.append(f"Found {n_warning} warning(s).")
    if n_info:
        summary_parts.append(f"Found {n_info} informational finding(s).")

    # Highlight the most impactful issues
    critical_issues = [rc for rc in root_causes if rc.severity == "critical"]
    if critical_issues:
        top_issue = critical_issues[0]
        summary_parts.append(f"Top issue: {top_issue.issue}")

    if problem_description:
        summary_parts.insert(0, f"User-reported problem: {problem_description}.")

    confidence = "High" if config_evidence else "Medium"
    if not log_evidence:
        confidence = "Medium" if config_evidence else "Low"

    return DlpDiagnosticsResponse(
        summary=" ".join(summary_parts),
        confidence=confidence,
        root_causes=root_causes,
        evidence=DlpEvidence(
            config=config_evidence,
            logs=log_evidence,
            code=code_evidence,
        ),
        recommendations=recommendations,
        unknowns=unknowns,
        event_trend=event_trend,
    )
