#!/usr/bin/env python3
"""
Scout Persona Runner
Queries LiteLLM free model fleet ($0 pool) to perform generic gap analysis
and propose next vertical slices for BACKLOG.md.
"""
import importlib.util
import os
import re
import subprocess
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from fleet import query_fleet, get_last_usage
from telemetry import record as record_telemetry

MODEL = os.getenv("SCOUT_MODEL", "scout-fleet")

_CODE_EXTS = {
    ".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".java", ".kt", ".rb", ".php", ".sh",
}
_EXTRA_SKIP_EXTS = {".yaml", ".yml", ".csv", ".toml"}


def _load_outline_filters() -> tuple[set[str], set[str]]:
    """Reuse SKIP_DIRS and SKIP_EXTS from outline-ast.py when available."""
    outline_path = os.path.join(SCRIPTS_DIR, "outline-ast.py")
    try:
        spec = importlib.util.spec_from_file_location("outline_ast", outline_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return set(getattr(mod, "SKIP_DIRS", ())), set(getattr(mod, "SKIP_EXTS", ()))
    except Exception:
        pass
    return {".git", "node_modules", ".worktrees", "skills", ".agents"}, {".png", ".svg", ".ico", ".lock"}


def _read_slice(path: str, max_chars: int = 1200, tail: bool = False) -> str:
    """Safely read a compact slice of a text file."""
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", errors="ignore") as f:
            content = f.read().strip()
        if len(content) <= max_chars:
            return content
        return content[-max_chars:] if tail else content[:max_chars]
    except Exception:
        return ""


def list_repo_files(repo_dir: str = ".", limit: int = 40) -> list[str]:
    """List tracked repository files generically via git ls-files, excluding assets and vendor/skill dirs."""
    skip_dirs, skip_exts = _load_outline_filters()
    skip_exts = skip_exts | _EXTRA_SKIP_EXTS
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "ls-files"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        files = []
        for path in proc.stdout.strip().splitlines():
            parts = path.split("/")
            if any(part in skip_dirs for part in parts[:-1]):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in skip_exts or path.endswith(".min.js") or path.endswith(".min.css"):
                continue
            files.append(path)
            if len(files) >= limit:
                break
        return files
    except Exception:
        return []


def get_recent_commits(repo_dir: str = ".", limit: int = 8) -> list[str]:
    """Return compact recent git commit summaries."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "log", f"-n{limit}", "--oneline"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
    except Exception:
        pass
    return []


def find_test_gaps(files: list[str], limit: int = 12) -> list[str]:
    """Identify source files that lack a corresponding test file by module stem."""
    test_names = []
    source_files = []
    for path in files:
        lower = path.lower()
        base = os.path.basename(lower)
        is_test = (
            "/tests/" in f"/{lower}"
            or "/test/" in f"/{lower}"
            or "__tests__" in lower
            or base.startswith("test_")
            or ".test." in base
            or ".spec." in base
            or "_test." in base
        )
        if is_test:
            test_names.append(lower)
        elif os.path.splitext(lower)[1] in _CODE_EXTS and not base.startswith("."):
            source_files.append(path)

    gaps = []
    for src in source_files:
        stem = os.path.splitext(os.path.basename(src).lower())[0].replace("-", "_")
        if stem in ("__init__", "main", "index", "cli"):
            continue
        if not any(stem in t.replace("-", "_") for t in test_names):
            gaps.append(src)
            if len(gaps) >= limit:
                break
    return gaps


def build_discovery_prompt(
    project_roadmap_path,
    backlog_path,
    designer_review: str = "",
    scope_path: str = "",
    discovery_path: str = "",
    repo_dir: str = ".",
) -> tuple[str, str]:
    """Assemble compact system and user prompts grounded in scope, discovery notes, commits, and test gaps."""
    roadmap = _read_slice(project_roadmap_path, max_chars=1000)
    backlog = _read_slice(backlog_path, max_chars=4000, tail=True)
    scope = _read_slice(scope_path, max_chars=1500)
    discovery = _read_slice(discovery_path, max_chars=1200)

    designer_section = f"\nDESIGNER UX/UI AUDIT FINDINGS:\n{designer_review}\n" if designer_review else ""
    roadmap_section = f"\nPROJECT ROADMAP:\n{roadmap}\n" if roadmap else ""
    scope_section = (
        f"\nPROJECT SCOPE BOUNDARIES (STRICTLY ENFORCE - REJECT FORBIDDEN AREAS):\n{scope}\n"
        if scope else ""
    )
    discovery_section = f"\nSTAGED DISCOVERY PROPOSALS (.amase/discovery.md):\n{discovery}\n" if discovery else ""

    # Check for pending global engine incidents if scouting the orchestrator itself
    engine_tasks = ""
    is_orchestrator = False
    try:
        is_orchestrator = os.path.samefile(repo_dir, ORCHESTRATOR_ROOT) or os.path.basename(os.path.abspath(repo_dir)) in ("orchestrator", "amase")
    except Exception:
        is_orchestrator = os.path.basename(os.path.abspath(repo_dir)) in ("orchestrator", "amase")

    if is_orchestrator:
        try:
            import engine_incident
            engine_tasks = engine_incident.format_scout_tasks(limit=2)
        except Exception:
            pass

    engine_section = (
        f"\nPENDING ORCHESTRATOR TOOL INCIDENTS REPORTED BY PROJECTS:\n{engine_tasks}\n"
        "Prioritize addressing these real engine bugs.\n"
        if engine_tasks else ""
    )

    # Extract completed tasks for strict duplicate prevention
    full_backlog = _read_slice(backlog_path, max_chars=200000)
    completed_titles = []
    if full_backlog:
        for line in full_backlog.splitlines():
            m = re.match(r'^- \[[xX]\] \*\*TASK-[0-9A-Z-]+:?\s*(.*?)\*\*', line)
            if m:
                completed_titles.append(m.group(1).strip())

    completed_section = ""
    if completed_titles:
        recent_completed = completed_titles[-25:]
        completed_section = (
            "\nALREADY COMPLETED FEATURES (STRICTLY FORBIDDEN TO RE-PROPOSE OR DUPLICATE):\n"
            + "\n".join(f"- {t}" for t in recent_completed)
            + "\n"
        )

    files = list_repo_files(repo_dir=repo_dir, limit=60)
    repo_files = ""
    if files:
        repo_files = (
            "\nEXISTING REPOSITORY FILES (Reference these exact file paths for - **Files:**):\n"
            + "\n".join(f"- {f}" for f in files[:40])
            + "\n"
        )

    gaps = find_test_gaps(files)
    test_gaps_section = ""
    if gaps:
        test_gaps_section = (
            "\nPOTENTIAL TEST COVERAGE GAPS (Source modules without matching test files):\n"
            + "\n".join(f"- {g}" for g in gaps)
            + "\n"
        )

    commits = get_recent_commits(repo_dir=repo_dir, limit=8)
    commits_section = ""
    if commits:
        commits_section = "\nRECENT COMMITS:\n" + "\n".join(f"- {c}" for c in commits) + "\n"

    backlog_slice = backlog[-1200:] if len(backlog) > 1200 else backlog

    user_prompt = f"""You are the Scout persona. Analyze this project's scope boundaries, discovery notes, recent commits, source files, test gaps, and recent backlog.
Discover the next 2 logical, minimal vertical slice tasks needed for this repository to advance.
Tasks MUST strictly adhere to the ALLOWED areas in the project scope boundaries and MUST NOT violate any FORBIDDEN rules.
Keep tasks minimal, atomic, and deterministic.

{scope_section}{roadmap_section}{discovery_section}{designer_section}{engine_section}{commits_section}{test_gaps_section}{completed_section}{repo_files}
RECENT BACKLOG:
{backlog_slice}

Respond ONLY with the markdown tasks ready for backlog triage, following the exact format:
- [ ] **TASK-XX: <Title>**
  - **Goal:** <Goal in 1 sentence>
  - **Files:** <Target files>
  - **Criteria:** <Deterministic verification test or command>
"""
    return user_prompt, engine_tasks


def discover_tasks(project_roadmap_path, backlog_path, designer_review="", scope_path="", discovery_path=""):
    with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "scout.md"), "r") as f:
        scout_prompt = f.read()

    user_prompt, engine_tasks = build_discovery_prompt(
        project_roadmap_path,
        backlog_path,
        designer_review=designer_review,
        scope_path=scope_path,
        discovery_path=discovery_path,
        repo_dir=os.getcwd(),
    )

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
                status="planned",
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

    if args.objective or args.dry_run:
        obj = args.objective or "Sample vertical slice task"
        task_id = "TASK-99"
        print(f"- [ ] **{task_id}: {obj}**")
        print(f"  - **Goal:** {obj}")
        print(f"  - **Files:** scripts/scout.py, amase")
        print(f"  - **Criteria:** python3 scripts/scout.py --objective \"{obj}\" --dry-run exits 0")
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
    if roadmap_file and os.path.exists(roadmap_file):
        print(f"  Roadmap: {roadmap_file}")
    else:
        print("  No roadmap provided – proceeding with default discovery.")
    print(f"  Scope:   {args.scope if (args.scope and os.path.exists(args.scope)) else 'None'}")
    print(f"  Backlog: {args.backlog}")

    tasks = discover_tasks(roadmap_file, args.backlog, designer_text, args.scope, args.discovery)
    if tasks:
        print("\nDiscovered Tasks from Free Fleet:")
        print(tasks)
        if args.append_discovery and os.path.exists(args.discovery):
            with open(args.discovery, "a") as f:
                f.write(f"\n{tasks}\n")
            print(f"[+] Appended discovered tasks to {args.discovery}")
