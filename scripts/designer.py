#!/usr/bin/env python3
"""
Designer Persona Runner
Audits extension UI/UX components (popup, options, floating buttons, Svelte components),
identifies ergonomic bottlenecks, and formats UX improvement specs for Scout discovery.
"""
import os
import sys
import json
import urllib.request

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")
MODEL = os.getenv("DESIGNER_MODEL", "coding-fleet")

def run_ux_review(target_dir):
    with open("/home/joao/dev/orchestrator/personas/designer.md", "r") as f:
        designer_prompt = f.read()

    # Collect UI component summaries
    ui_files = [
        "wxt.config.ts",
        "src/entrypoints/popup/App.svelte",
        "src/entrypoints/popup/index.html",
        "src/entrypoints/options/Options.svelte",
        "src/entrypoints/options/index.html",
        "src/entrypoints/floating.content.ts",
        "src/lib/applications.svelte",
        "src/lib/components/tabs.svelte"
    ]

    context = []
    for rel_path in ui_files:
        full_path = os.path.join(target_dir, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                content = f.read()
                context.append(f"--- File: {rel_path} ---\n{content}\n")

    combined_context = "\n".join(context)

    user_prompt = f"""You are Designer. Perform a comprehensive UX/UI review of the Kandidat browser extension based on these component source files:

{combined_context}

Evaluate:
1. Navigation & Access: Why did user see Options embedded in chrome://extensions/?id=... instead of a standalone tab? How do users jump to Options from Popup?
2. Surface Role Separation: Why is having a 'Fill' button in the toolbar popup redundant when we have in-page floating buttons on job applications? How should the Popup be redesigned as an Application Tracker Hub?
3. Visual Hierarchy & Svelte 5 Modernization: Are we using deprecated syntax in tabs/components? Is feedback (copied, submitted, filled) evident?
4. Concrete Recommendations for Scout (Discovery): Provide clear UX specs that Scout can translate directly into engineering backlog tasks.
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
    target = sys.argv[1] if len(sys.argv) > 1 else "/home/joao/dev/kandidat"
    run_ux_review(target)
