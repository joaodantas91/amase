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
MODEL = os.getenv("SCOUT_MODEL", "coding-fleet")

def discover_tasks(project_roadmap_path, backlog_path):
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

    user_prompt = f"""You are the Scout persona. Analyze this project's roadmap and current backlog.
Discover the next 2 logical, minimal vertical slice tasks needed for this web extension to advance towards real-world usability on job platforms (e.g., Lever, Greenhouse, Workday, LinkedIn).

ROADMAP:
{roadmap[:3000]}

CURRENT BACKLOG:
{backlog}

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
        "temperature": 0.2,
        "max_tokens": 800
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
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

    print(f"Scout: Querying free model fleet for project '{os.path.basename(os.getcwd())}'...")
    print(f"  Roadmap: {roadmap_file if os.path.exists(roadmap_file) else 'None (auto-inferring)'}")
    print(f"  Backlog: {args.backlog}")

    tasks = discover_tasks(roadmap_file, args.backlog)
    if tasks:
        print("\nDiscovered Tasks from Free Fleet:")
        print(tasks)
