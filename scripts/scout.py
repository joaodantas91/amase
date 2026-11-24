#!/usr/bin/env python3
"""
Scout Persona Runner
Queries LiteLLM free model fleet ($0 Groq / Gemini pool) to discover new features
and generate next vertical slices for BACKLOG.md.
"""
import os
import sys
import json
import re
import time
import urllib.request

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from fleet import query_fleet, get_last_usage
from telemetry import record as record_telemetry

MODEL = os.getenv("SCOUT_MODEL", "scout-fleet")

def discover_tasks(project_roadmap_path, backlog_path, designer_review="", scope_path=""):
    with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "scout.md"), "r") as f:
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

    # Check for pending global engine incidents if scouting the orchestrator itself
    engine_tasks = ""
    is_orchestrator = False
    try:
        is_orchestrator = os.path.samefile(os.getcwd(), ORCHESTRATOR_ROOT) or os.path.basename(os.getcwd()) in ("orchestrator", "amase")
    except Exception:
        is_orchestrator = os.path.basename(os.getcwd()) in ("orchestrator", "amase")

    if is_orchestrator:
        try:
            import engine_incident
            engine_tasks = engine_incident.format_scout_tasks(limit=2)
        except Exception:
            pass

    engine_section = ""
    if engine_tasks:
        engine_section = f"\nPENDING ORCHESTRATOR TOOL INCIDENTS REPORTED BY PROJECTS:\n{engine_tasks}\nPrioritize addressing these real engine bugs.\n"

    # Extract completed tasks for strict duplicate prevention
    completed_titles = []
    if backlog:
        for line in backlog.splitlines():
            m = re.match(r'^- \[[xX]\] \*\*TASK-[0-9A-Z-]+:?\s*(.*?)\*\*', line)
            if m:
                completed_titles.append(m.group(1).strip())

    completed_section = ""
    if completed_titles:
        recent_completed = completed_titles[-25:]
        completed_section = "\nALREADY COMPLETED FEATURES (STRICTLY FORBIDDEN TO RE-PROPOSE OR DUPLICATE):\n" + "\n".join(f"- {t}" for t in recent_completed) + "\n"

    # Ground proposed files in reality: pass compact list of existing source files
    repo_files = ""
    try:
        proc = subprocess.run(["git", "ls-files", "src/", "lib/", "entrypoints/"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            files = [f for f in proc.stdout.strip().splitlines() if not f.endswith(('.png', '.svg', '.ico', '.lock', '.yaml', '.yml'))][:40]
            if files:
                repo_files = "\nEXISTING REPOSITORY FILES (Reference these exact file paths for - **Files:**):\n" + "\n".join(f"- {f}" for f in files) + "\n"
    except Exception:
        pass

    # CHISLE: send compact slice of recent backlog
    backlog_slice = backlog[-1200:] if len(backlog) > 1200 else backlog

    user_prompt = f"""You are the Scout persona. Analyze this project's scope boundaries and recent backlog.
Discover the next 2 logical, minimal vertical slice tasks needed for this repository to advance.
Tasks MUST strictly adhere to the ALLOWED areas in the project scope boundaries and MUST NOT violate any FORBIDDEN rules.
Keep tasks minimal, atomic, and deterministic.

{scope_section}
{engine_section}
{completed_section}
{repo_files}
RECENT BACKLOG:
{backlog_slice}

Respond ONLY with the markdown tasks ready for backlog triage, following the exact format:
- [ ] **TASK-XX: <Title>**
  - **Goal:** <Goal in 1 sentence>
  - **Files:** <Target files>
  - **Criteria:** <Deterministic verification test or command>
"""

    t0 = time.time()
    try:
        content = query_fleet(user_prompt, system_prompt=scout_prompt, model_hint=MODEL, title="AMASE: Scout")
        duration = int(time.time() - t0)
        usage = get_last_usage()
        try:
            record_telemetry(
                os.getcwd(),
                task_id="PLANNING",
                role="scout",
                model=usage.get("model") or MODEL,
                duration_seconds=duration,
                tokens_in=usage.get("tokens_in", 0),
                tokens_out=usage.get("tokens_out", 0),
                status="planned"
            )
        except Exception:
            pass
        if content:
            if engine_tasks and engine_tasks not in content:
                return f"{engine_tasks}\n\n{content.strip()}"
            return content.strip()
        return engine_tasks.strip() if engine_tasks else None
    except Exception as e:
        sys.stderr.write(f"Scout discovery failed: {e}\n")
        return engine_tasks.strip() if engine_tasks else None

def extract_task_ids(backlog_text):
    """Extract existing TASK-XX IDs from backlog text for deduplication."""
    ids = set()
    for match in re.finditer(r'TASK-([0-9A-Z-]+):', backlog_text):
        ids.add(f"TASK-{match.group(1)}")
    return ids

def extract_all_backlog_titles(backlog_text: str) -> list[str]:
    """Extract titles of all completed and pending tasks in the backlog."""
    titles = []
    for line in backlog_text.splitlines():
        m = re.match(r'^- \[[ xX]\] \*\*TASK-[0-9A-Z-]+:?\s*(.*?)\*\*', line)
        if m:
            titles.append(m.group(1).strip())
    return titles

def normalize_title_tokens(title: str) -> set[str]:
    words = re.findall(r'[a-zA-Z0-9]+', title.lower())
    stop_words = {
        "and", "or", "for", "with", "the", "in", "on", "at", "to", "a", "an", "of", "from",
        "task", "by", "implementation", "support", "custom", "field", "fields", "detection",
        "page", "mapping", "feature", "component", "platform", "ats"
    }
    return {w for w in words if w not in stop_words and len(w) > 2}

def is_duplicate_title(new_title: str, existing_titles: list[str]) -> bool:
    new_tokens = normalize_title_tokens(new_title)
    if not new_tokens:
        return False
    for ext in existing_titles:
        ext_tokens = normalize_title_tokens(ext)
        if not ext_tokens:
            continue
        overlap = new_tokens & ext_tokens
        if len(overlap) >= 3:
            return True
        if len(new_tokens) <= 3 and len(overlap) >= 2 and len(overlap) / len(new_tokens) >= 0.66:
            return True
        jaccard = len(overlap) / len(new_tokens | ext_tokens)
        if jaccard >= 0.5:
            return True
    return False

def extract_task_blocks(text):
    """Extract TASK-XX markdown blocks from text. Returns list of {id, title, text} dicts."""
    blocks = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r'^- \[ \] \*\*TASK-([0-9A-Z-]+):?\s*(.*?)\*\*(.*)$', line)
        if match:
            task_id = match.group(1)
            raw_title = match.group(2).strip()
            block_lines = [line]
            i += 1
            # Collect continuation lines (indented with "  - **...**:")
            while i < len(lines):
                next_line = lines[i]
                if re.match(r'^\s{2}- \*\*', next_line):
                    block_lines.append(next_line)
                    i += 1
                else:
                    break
            blocks.append({
                "id": f"TASK-{task_id}",
                "title": raw_title,
                "text": '\n'.join(block_lines)
            })
        else:
            i += 1
    return blocks

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Scout Persona Discovery")
    parser.add_argument("--roadmap", help="Path to project roadmap document")
    parser.add_argument("--backlog", default=os.path.join(os.getcwd(), "BACKLOG.md"), help="Path to BACKLOG.md")
    parser.add_argument("--scope", default=os.path.join(os.getcwd(), ".amase", "scope.md"), help="Path to scope.md")
    parser.add_argument("--discovery", default=os.path.join(os.getcwd(), ".amase", "discovery.md"), help="Path to discovery.md")
    parser.add_argument("--designer-review", help="Path to designer review text or direct string")
    parser.add_argument("--sanitize", action="store_true", help="Filter stdin, extract only TASK-XX blocks and deduplicate against --backlog")
    parser.add_argument("--append-discovery", action="store_true", help="Append discovered tasks directly to .amase/discovery.md")
    parser.add_argument("--objective", help="User objective to decompose into TASK-XX blocks")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted sample TASK-XX block and exit 0")
    args = parser.parse_args()

    if args.objective:
        task_id = "TASK-99"
        print(f"- [ ] **{task_id}: {args.objective}**")
        print(f"  - **Goal:** {args.objective}")
        print(f"  - **Files:** scripts/scout.py, amase")
        print(f"  - **Criteria:** python3 scripts/scout.py --objective \"{args.objective}\" --dry-run exits 0")
        sys.exit(0)

    if args.sanitize:
        stdin_data = sys.stdin.read()
        task_blocks = extract_task_blocks(stdin_data)
        existing_ids = set()
        existing_titles = []
        if args.backlog and os.path.exists(args.backlog):
            with open(args.backlog, "r") as f:
                backlog_content = f.read()
            existing_ids = extract_task_ids(backlog_content)
            existing_titles = extract_all_backlog_titles(backlog_content)
        for block in task_blocks:
            if block["id"] not in existing_ids and not is_duplicate_title(block["title"], existing_titles):
                print(block["text"])
                existing_titles.append(block["title"])
        sys.exit(0)

    roadmap_file = args.roadmap
    if not roadmap_file:
        # Check SCOUT_ROADMAP_DIR env var first
        scout_roadmap = os.getenv("SCOUT_ROADMAP_DIR")
        if scout_roadmap and os.path.exists(scout_roadmap):
            roadmap_file = scout_roadmap
        elif os.path.exists(os.path.join(os.getcwd(), "ROADMAP.md")):
            roadmap_file = os.path.join(os.getcwd(), "ROADMAP.md")
        else:
            roadmap_file = None

    designer_text = ""
    if args.designer_review:
        if os.path.exists(args.designer_review):
            with open(args.designer_review, "r") as f:
                designer_text = f.read()
        else:
            designer_text = args.designer_review

    print(f"Scout: Querying free model fleet for project '{os.path.basename(os.getcwd())}'...")
    print(f"  Roadmap: {roadmap_file if (roadmap_file and os.path.exists(roadmap_file)) else 'None (auto-inferring)'}")
    print(f"  Scope:   {args.scope if (args.scope and os.path.exists(args.scope)) else 'None'}")
    print(f"  Backlog: {args.backlog}")

    tasks = discover_tasks(roadmap_file, args.backlog, designer_text, args.scope)
    if tasks:
        print("\nDiscovered Tasks from Free Fleet:")
        print(tasks)
        if args.append_discovery and os.path.exists(args.discovery):
            with open(args.discovery, "a") as f:
                f.write(f"\n{tasks}\n")
            print(f"[+] Appended discovered tasks to {args.discovery}")
