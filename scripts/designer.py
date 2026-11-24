#!/usr/bin/env python3
"""
Designer Persona Runner
Audits extension UI/UX components (popup, options, floating buttons, Svelte components),
identifies ergonomic bottlenecks, and formats UX improvement specs for Scout discovery.
Powered by UI/UX Pro Max design intelligence skill.
"""
import os
import sys
import json
import subprocess
import urllib.request

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")
MODEL = os.getenv("DESIGNER_MODEL", "designer-fleet")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)
SKILL_SEARCH = os.path.join(ORCHESTRATOR_ROOT, "skills", "ui-ux-pro-max", "scripts", "search.py")

def get_design_intelligence(query="browser extension developer tool dark mode dashboard"):
    """Query UI/UX Pro Max skill for design system, color tokens, and UX guidelines."""
    intel = []
    if os.path.exists(SKILL_SEARCH):
        try:
            ds_output = subprocess.check_output(
                ["python3", SKILL_SEARCH, query, "--design-system"],
                text=True, timeout=10
            )
            intel.append(f"--- UI/UX PRO MAX RECOMMENDED DESIGN SYSTEM ---\n{ds_output}\n")
        except Exception as e:
            sys.stderr.write(f"UI/UX Pro Max design-system query failed: {e}\n")

        try:
            ux_output = subprocess.check_output(
                ["python3", SKILL_SEARCH, "form inputs buttons dark mode", "--domain", "ux"],
                text=True, timeout=10
            )
            intel.append(f"--- UI/UX PRO MAX FORM & INTERACTION GUIDELINES ---\n{ux_output}\n")
        except Exception as e:
            sys.stderr.write(f"UI/UX Pro Max UX query failed: {e}\n")

    return "\n".join(intel)

def run_ux_review(target_dir):
    with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "designer.md"), "r") as f:
        designer_prompt = f.read()

    # Collect UI component summaries
    ui_files = [
        "wxt.config.ts",
        "src/entrypoints/popup/App.svelte",
        "src/entrypoints/popup/app.css",
        "src/entrypoints/options/Options.svelte",
        "src/entrypoints/options/ProfileManager.svelte",
        "src/entrypoints/floating.content.ts",
        "src/lib/applications.svelte"
    ]

    context = []
    for rel_path in ui_files:
        full_path = os.path.join(target_dir, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                content = f.read()
                # Cap file length to prevent bloated context
                lines = content.splitlines()
                if len(lines) > 80:
                    truncated = "\n".join(lines[:80]) + f"\n... [truncated {len(lines) - 80} lines] ..."
                    context.append(f"--- File: {rel_path} (preview) ---\n{truncated}\n")
                else:
                    context.append(f"--- File: {rel_path} ---\n{content}\n")

    combined_context = "\n".join(context)
    design_intel = get_design_intelligence()

    user_prompt = f"""You are Designer, backed by the UI/UX Pro Max design intelligence skill.
Perform a comprehensive UX/UI review of the Kandidat browser extension based on these component source files:

{combined_context}

{design_intel}

Evaluate & Specify:
1. Design System Tokens: Define standardized CSS variables (--color-bg-*, --color-border-*, --color-text-*, --color-primary-*, --space-*, --font-*, --radius-*) to eliminate all scattered raw hex values.
2. Form & Control Uniformity: Specify unified styling for all inputs, textareas, selects, and buttons across both Popup and Options so they share identical height, padding, font-size, background, and focus glow.
3. Card & Layout Hierarchy: Clean responsive 2-column grid for dense form sections, full-width textareas, card containers with subtle borders.
4. Actionable Task Specs: Provide concrete specifications for engineering backlog tasks (e.g. TASK-DS-01).
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": designer_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1200
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
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = data["choices"][0]["message"]["content"]
            print(result)
            return result
    except Exception as e:
        print(f"[-] Designer UX review failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    run_ux_review(target)
