#!/usr/bin/env python3
"""
Sentinel Persona Runner
Audits recent git commits/diffs for security vulnerabilities, DOM injection risks,
Manifest V3 permission creep, and code duplication (PONYTAIL Rung 2 violations).
Outputs report to AUDIT.md.
"""
import os
import sys
import json
import time
import subprocess
import urllib.request

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from fleet import query_fleet, get_last_usage
from telemetry import record as record_telemetry

MODEL = os.getenv("SENTINEL_MODEL", "sentinel-fleet")

def run_audit(target_dir, base_ref="HEAD~1"):
    try:
        result = subprocess.run(
            ["git", "-C", target_dir, "diff", base_ref],
            capture_output=True, text=True, timeout=30
        )
        diff = result.stdout if result.returncode == 0 else ""
    except Exception:
        diff = ""

    with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "sentinel.md"), "r") as f:
        sentinel_prompt = f.read()

    user_prompt = f"""You are Sentinel. Audit this recent git diff for:
1. DOM injection risks (innerHTML, outerHTML, unescaped templates)
2. Prototype pollution or unsafe setter overrides
3. Manifest V3 permission escalation or broad host patterns (<all_urls>)
4. Code duplication (PONYTAIL Rung 2): Are new helpers reinventing utilities that already exist in src/core/?
5. Missing input guards on form autofill fields

DIFF TO AUDIT:
{diff[:4000]}

Format your response following the AUDIT.md contract:
- [CRITICAL] / [HIGH] / [MEDIUM] / [LOW] / [INFO]
If clean, report 'Core invariants verified clean'.
"""

    t0 = time.time()
    try:
        result = query_fleet(user_prompt, system_prompt=sentinel_prompt, model_hint=MODEL, title="AMASE: Sentinel")
        duration = int(time.time() - t0)
        usage = get_last_usage()
        try:
            record_telemetry(
                target_dir,
                task_id="AUDIT",
                role="sentinel",
                model=usage.get("model") or MODEL,
                duration_seconds=duration,
                tokens_in=usage.get("tokens_in", 0),
                tokens_out=usage.get("tokens_out", 0),
                status="clean" if "Core invariants verified clean" in (result or "") else "flagged"
            )
        except Exception:
            pass
        if result:
            print(result)
            return result
        return None
    except Exception as e:
        print(f"[-] Sentinel audit failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        target = sys.argv[1] if len(sys.argv) > 1 else "."
        base = sys.argv[2] if len(sys.argv) > 2 else "HEAD~1"
        with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "sentinel.md"), "r") as f:
            sentinel_prompt = f.read()
        # Reconstruct diff for display (same logic as run_audit)
        try:
            result = subprocess.run(
                ["git", "-C", target, "diff", base],
                capture_output=True, text=True, timeout=30
            )
            diff = result.stdout if result.returncode == 0 else ""
        except Exception:
            diff = ""
        user_prompt = f"""You are Sentinel. Audit this recent git diff for:
1. DOM injection risks (innerHTML, outerHTML, unescaped templates)
2. Prototype pollution or unsafe setter overrides
3. Manifest V3 permission escalation or broad host patterns (<all_urls>)
4. Code duplication (PONYTAIL Rung 2): Are new helpers reinventing utilities that already exist in src/core/?
5. Missing input guards on form autofill fields

DIFF TO AUDIT:
{diff[:4000]}

Format your response following the AUDIT.md contract:
- [CRITICAL] / [HIGH] / [LOW] / [INFO]
If clean, report 'Core invariants verified clean'.
"""
        print(user_prompt)
        import sys as _sys
        _sys.exit(0)
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    base = sys.argv[2] if len(sys.argv) > 2 else "HEAD~1"
    run_audit(target, base)
