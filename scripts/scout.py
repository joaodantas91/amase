#!/usr/bin/env python3
"""
Scout Persona Runner
Queries LiteLLM free model fleet ($0 Groq / Gemini pool) to discover new features
and generate next vertical slices for BACKLOG.md.
"""
import os
import sys
import json
import urllib.request

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")
MODEL = os.getenv("SCOUT_MODEL", "scout-fleet")

def discover_tasks(project_roadmap_path, backlog_path, designer_review=""):
    with open("/home/joao/dev/orchestrator/personas/scout.md", "r") as f:
        scout_prompt = f.read()

    roadmap = ""
    if os.path.exists(project_roadmap_path):
        with open(project_roadmap_path, "r") as f:
            roadmap = f.read()

    backlog = ""
    if os.path.exists(backlog_path):
        with open(backlog_path, "r") as f:
            backlog = f.read()

    designer_section = ""
    if designer_review:
        designer_section = f"\nDESIGNER UX/UI AUDIT FINDINGS:\n{designer_review}\n"

    # CHISLE: send recent backlog tasks instead of 4000-word whole history
    backlog_slice = backlog[-3500:] if len(backlog) > 3500 else backlog

    user_prompt = f"""You are the Scout persona. Analyze this project's roadmap, current backlog, and UX/UI Designer findings.
Discover the next 2 logical, minimal vertical slice tasks needed for this web extension to advance towards real-world usability and ergonomic UI.
If UX/UI findings are provided, prioritize translating them into concrete, testable UI engineering slices.

ROADMAP:
{roadmap[:3000]}
{designer_section}
RECENT BACKLOG:
{backlog_slice}

Respond ONLY with the markdown tasks ready to append to BACKLOG.md, following the exact format:
- [ ] **TASK-XX: <Title>**
  - **Goal:** <Goal>
  - **Files:** <Target files>
  - **Criteria:** <Verification criteria>
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": scout_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2048
    }

    req = urllib.request.Request(
        LITELLM_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return content.strip()
    except Exception as e:
        sys.stderr.write(f"Scout discovery failed: {e}\n")
        return None

if __name__ == "__main__":
    import argparse
    import glob

    parser = argparse.ArgumentParser(description="Scout Persona Discovery")
    parser.add_argument("--roadmap", help="Path to project roadmap document")
    parser.add_argument("--backlog", default=os.path.join(os.getcwd(), "BACKLOG.md"), help="Path to BACKLOG.md")
    parser.add_argument("--designer-review", help="Path to designer review text or direct string")
    args = parser.parse_args()

    roadmap_file = args.roadmap
    if not roadmap_file:
        # Auto-detect from joao-os based on current folder name
        project_name = os.path.basename(os.getcwd()).lower()
        candidates = glob.glob(f"/home/joao/dev/joao-os/40 Projetos/*{project_name}*.md")
        if candidates:
            roadmap_file = candidates[0]
        else:
            roadmap_file = os.path.join(os.getcwd(), "ROADMAP.md")

    designer_text = ""
    if args.designer_review:
        if os.path.exists(args.designer_review):
            with open(args.designer_review, "r") as f:
                designer_text = f.read()
        else:
            designer_text = args.designer_review

    print(f"Scout: Querying free model fleet for project '{os.path.basename(os.getcwd())}'...")
    print(f"  Roadmap: {roadmap_file if os.path.exists(roadmap_file) else 'None (auto-inferring)'}")
    print(f"  Backlog: {args.backlog}")

    tasks = discover_tasks(roadmap_file, args.backlog, designer_text)
    if tasks:
        print("\nDiscovered Tasks from Free Fleet:")
        print(tasks)
