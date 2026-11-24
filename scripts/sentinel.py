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
import subprocess
import urllib.request

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(os.path.dirname(SCRIPTS_DIR))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from fleet import query_fleet

MODEL = os.getenv("SENTINEL_MODEL", "opencode/nemotron-3.5-lightning-free")

def run_audit(target_dir, base_ref="HEAD~1"):
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

    try:
        result = query_fleet(user_prompt, system_prompt=sentinel_prompt, model_hint=MODEL, title="AMASE: Sentinel")
        if result:
            print(result)
            return result
        return None
    except Exception as e:
        print(f"[-] Sentinel audit failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    base = sys.argv[2] if len(sys.argv) > 2 else "HEAD~1"
    run_audit(target, base)
