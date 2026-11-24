#!/usr/bin/env python3
"""
AMASE Global Engine Incident Telemetry & Diagnostic Registry

Records tool bugs, script crashes, and runtime limitations encountered
when running in ANY target project into central ~/.amase/engine_issues.jsonl.
Ingested exclusively when running AMASE inside the orchestrator repo to
autonomously convert real-world tool failures into self-healing backlog tasks.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_global_incidents_path() -> str:
    """Return path to global engine issues registry (~/.amase/engine_issues.jsonl)."""
    amase_home = os.path.expanduser("~/.amase")
    os.makedirs(amase_home, exist_ok=True)
    return os.path.join(amase_home, "engine_issues.jsonl")


def record_incident(
    script: str,
    signature: str,
    message: str,
    project_dir: str = "",
    stack_trace: str = ""
):
    """Record an orchestrator tool incident into global registry."""
    incident_file = get_global_incidents_path()
    entry = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "script": script,
        "signature": signature.upper(),
        "message": message.strip(),
        "project_dir": os.path.abspath(project_dir) if project_dir else os.getcwd(),
        "stack_trace": stack_trace.strip()[:2000] if stack_trace else "",
        "status": "pending",
    }

    with open(incident_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[EngineIncident] Registered: {entry['signature']} in {script} (status: pending)")
    return entry


def list_incidents(status: str = "pending"):
    """List recorded engine incidents filtered by status."""
    incident_file = get_global_incidents_path()
    if not os.path.isfile(incident_file):
        return []

    incidents = []
    with open(incident_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if status == "all" or data.get("status") == status:
                        incidents.append(data)
                except Exception:
                    continue
    return incidents


def format_scout_tasks(limit: int = 3):
    """Format pending engine incidents into TASK-ENG-XX markdown blocks for Scout."""
    pending = list_incidents(status="pending")
    if not pending:
        return ""

    # Group by signature + script to avoid duplicate tasks
    grouped = {}
    for inc in pending:
        key = (inc.get("signature", "ENGINE_ERROR"), inc.get("script", "orchestrator"))
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(inc)

    blocks = []
    idx = 1
    for (sig, script), items in list(grouped.items())[:limit]:
        sample = items[-1]
        msg = sample.get("message", "Tool limitation encountered")
        proj_base = os.path.basename(sample.get("project_dir", "target-project"))
        task_id = f"TASK-ENG-{idx:02d}"
        idx += 1

        target_file = script
        if not target_file.startswith("scripts/") and not target_file == "amase":
            target_file = f"scripts/{os.path.basename(script)}"

        block = (
            f"- [ ] **{task_id}: Resolve {sig} in {os.path.basename(script)}**\n"
            f"  - **Goal:** Fix engine limitation ({sig}) observed in project '{proj_base}': {msg}\n"
            f"  - **Files:** {target_file}\n"
            f"  - **Criteria:** python3 -m py_compile {target_file} 2>/dev/null || bash -n {target_file}; .amase/test-gate.sh passes."
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def resolve_incidents(signature: str):
    """Mark all pending incidents with given signature as resolved."""
    incident_file = get_global_incidents_path()
    if not os.path.isfile(incident_file):
        return 0

    lines = []
    resolved_count = 0
    with open(incident_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if data.get("signature", "").upper() == signature.upper() and data.get("status") == "pending":
                        data["status"] = "resolved"
                        data["resolved_at"] = datetime.now(timezone.utc).astimezone().isoformat()
                        resolved_count += 1
                    lines.append(data)
                except Exception:
                    continue

    if resolved_count > 0:
        with open(incident_file, "w") as f:
            for item in lines:
                f.write(json.dumps(item) + "\n")

    return resolved_count


def main():
    parser = argparse.ArgumentParser(description="AMASE Engine Incident Registry")
    parser.add_argument("--record", action="store_true", help="Record a new engine incident")
    parser.add_argument("--script", default="", help="Script path where error occurred")
    parser.add_argument("--signature", default="ENGINE_ERROR", help="Incident category signature")
    parser.add_argument("--message", default="", help="Error summary or diagnostic reason")
    parser.add_argument("--project", default="", help="Target project root directory")
    parser.add_argument("--stack", default="", help="Optional error stack trace")
    parser.add_argument("--list", action="store_true", help="List registered engine incidents")
    parser.add_argument("--status", default="pending", help="Filter for list: pending, resolved, all")
    parser.add_argument("--format-scout", action="store_true", help="Format pending incidents as Scout TASK-ENG blocks")
    parser.add_argument("--resolve", default="", help="Signature to mark as resolved")

    args = parser.parse_args()

    if args.record:
        if not args.script or not args.message:
            print("[-] Error: --script and --message required for recording.")
            sys.exit(1)
        record_incident(
            script=args.script,
            signature=args.signature,
            message=args.message,
            project_dir=args.project,
            stack_trace=args.stack
        )
        sys.exit(0)

    if args.resolve:
        count = resolve_incidents(args.resolve)
        print(f"[+] Marked {count} incidents with signature '{args.resolve}' as resolved.")
        sys.exit(0)

    if args.format_scout:
        tasks = format_scout_tasks()
        if tasks:
            print(tasks)
        else:
            print("[-] No pending engine incidents found.")
        sys.exit(0)

    if args.list:
        incidents = list_incidents(args.status)
        if not incidents:
            print(f"[+] No engine incidents found (status={args.status}).")
            sys.exit(0)
        print(f"=== AMASE Engine Incidents ({len(incidents)} total, filter: {args.status}) ===")
        for inc in incidents:
            ts = inc.get("timestamp", "").split(".")[0]
            sig = inc.get("signature")
            script = os.path.basename(inc.get("script", ""))
            proj = os.path.basename(inc.get("project_dir", ""))
            st = inc.get("status")
            msg = inc.get("message")
            print(f"[{ts}] [{st.upper()}] {sig} in {script} ({proj}): {msg}")

        retro_path = os.path.expanduser("~/.amase/retrospectives.jsonl")
        if os.path.exists(retro_path):
            retros = []
            with open(retro_path, "r") as f:
                for l in f:
                    if l.strip():
                        try:
                            retros.append(json.loads(l))
                        except Exception:
                            pass
            if retros:
                print(f"\n=== AMASE Worker Retrospectives ({len(retros)} total in ~/.amase/retrospectives.jsonl) ===")
                for r in retros[-10:]:
                    ts = r.get("timestamp", "").split(".")[0]
                    sig = r.get("failure_signature", "FAIL")
                    task = r.get("task_id", "")
                    proj = r.get("project_name", "")
                    model = r.get("model", "")
                    reason = r.get("reason", "")
                    print(f"[{ts}] [{sig}] {task} ({proj}) via {model}: {reason}")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
