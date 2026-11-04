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

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")
MODEL = os.getenv("SENTINEL_MODEL", "sentinel-fleet")

def run_audit(target_dir, base_ref="HEAD~1"):
    os.chdir(target_dir)
    diff = subprocess.check_output(["git", "diff", f"{base_ref}..HEAD"], text=True)
    if not diff.strip():
        print("[+] Diff is empty. Nothing to audit.")
        return

    with open("/home/joao/dev/orchestrator/personas/sentinel.md", "r") as f:
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

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sentinel_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 800
    }

    try:
        req = urllib.request.Request(
            LITELLM_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = data["choices"][0]["message"]["content"]
            print(result)
            return result
    except Exception as e:
        print(f"[-] Sentinel audit failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    base = sys.argv[2] if len(sys.argv) > 2 else "HEAD~1"
    run_audit(target, base)
