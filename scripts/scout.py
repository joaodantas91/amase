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

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from fleet import query_fleet

MODEL = os.getenv("SCOUT_MODEL", "opencode/nemotron-3.5-lightning-free")

def discover_tasks(project_roadmap_path, backlog_path, designer_review="", scope_path=""):
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

    scope = ""
    if scope_path and os.path.exists(scope_path):
        with open(scope_path, "r") as f:
            scope = f.read()

    designer_section = ""
    if designer_review:
        designer_section = f"\nDESIGNER UX/UI AUDIT FINDINGS:\n{designer_review}\n"

    scope_section = ""
    if scope:
        scope_section = f"\nPROJECT SCOPE BOUNDARIES (STRICTLY ENFORCE - REJECT FORBIDDEN AREAS):\n{scope}\n"

    # CHISLE: send compact slice of recent backlog
    backlog_slice = backlog[-1200:] if len(backlog) > 1200 else backlog

    user_prompt = f"""You are the Scout persona. Analyze this project's scope boundaries and recent backlog.
Discover the next 2 logical, minimal vertical slice tasks needed for this repository to advance.
Tasks MUST strictly adhere to the ALLOWED areas in the project scope boundaries and MUST NOT violate any FORBIDDEN rules.
Keep tasks minimal, atomic, and deterministic.

{scope_section}
RECENT BACKLOG:
{backlog_slice}

Respond ONLY with the markdown tasks ready for backlog triage, following the exact format:
- [ ] **TASK-XX: <Title>**
  - **Goal:** <Goal in 1 sentence>
  - **Files:** <Target files>
  - **Criteria:** <Deterministic verification test or command>
"""

    try:
        content = query_fleet(user_prompt, system_prompt=scout_prompt, model_hint=MODEL, title="AMASE: Scout")
        return content.strip() if content else None
    except Exception as e:
        sys.stderr.write(f"Scout discovery failed: {e}\n")
        return None

if __name__ == "__main__":
    import argparse
    import glob

    parser = argparse.ArgumentParser(description="Scout Persona Discovery")
    parser.add_argument("--roadmap", help="Path to project roadmap document")
    parser.add_argument("--backlog", default=os.path.join(os.getcwd(), "BACKLOG.md"), help="Path to BACKLOG.md")
    parser.add_argument("--scope", default=os.path.join(os.getcwd(), ".amase", "scope.md"), help="Path to scope.md")
    parser.add_argument("--discovery", default=os.path.join(os.getcwd(), ".amase", "discovery.md"), help="Path to discovery.md")
    parser.add_argument("--designer-review", help="Path to designer review text or direct string")
    parser.add_argument("--append-discovery", action="store_true", help="Append discovered tasks directly to .amase/discovery.md")
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
    print(f"  Scope:   {args.scope if os.path.exists(args.scope) else 'None'}")
    print(f"  Backlog: {args.backlog}")

    tasks = discover_tasks(roadmap_file, args.backlog, designer_text, args.scope)
    if tasks:
        print("\nDiscovered Tasks from Free Fleet:")
        print(tasks)
        if args.append_discovery and os.path.exists(args.discovery):
            with open(args.discovery, "a") as f:
                f.write(f"\n{tasks}\n")
            print(f"[+] Appended discovered tasks to {args.discovery}")
