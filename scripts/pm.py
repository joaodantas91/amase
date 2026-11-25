#!/usr/bin/env python3
"""
Project Manager (pm) Persona Runner
Decomposes user objectives and project status into 1-3 minimal, atomic,
verifiable vertical-slice tasks grounded in real repository files and scope.
"""
import argparse
import os
import re
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from fleet import get_last_usage, query_fleet
import scout
import status as status_mod
from telemetry import record as record_telemetry

MODEL = os.getenv("PM_MODEL", "scout-fleet")


def next_task_number(backlog_text: str) -> int:
    """Return the next sequential integer task number after existing TASK-XX IDs."""
    max_num = 0
    for task_id in scout.extract_task_ids(backlog_text):
        match = re.match(r"^TASK-(\d+)$", task_id)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def collect_status_summary(repo_dir: str, status_input: str = "") -> str:
    """Resolve status context from explicit text/file or live repository inspection."""
    if status_input:
        if os.path.isfile(status_input):
            return scout._read_slice(status_input, max_chars=1500)
        return status_input.strip()[:1500]

    ptype = status_mod.detect_project_type(repo_dir)
    git_state = status_mod.get_git_state(repo_dir)
    next_task, pending_count, total = status_mod.get_backlog_stats(repo_dir)
    lines = [
        f"Project Type: {ptype}",
        f"Working Tree: {git_state}",
        f"Backlog: {total - pending_count}/{total} completed, {pending_count} pending",
    ]
    if next_task:
        lines.append(f"Next Active Task: {next_task}")
    return "\n".join(lines)


def build_decomposition_prompt(
    objective: str,
    backlog_path: str = "",
    scope_path: str = "",
    status_input: str = "",
    repo_dir: str = ".",
) -> str:
    """Assemble a compact prompt grounded in objective, status, scope, backlog, and git ls-files."""
    scope = scout._read_slice(scope_path, max_chars=1500)
    full_backlog = scout._read_slice(backlog_path, max_chars=200000)
    status_summary = collect_status_summary(repo_dir, status_input)

    next_num = next_task_number(full_backlog)
    existing_titles = scout.extract_all_backlog_titles(full_backlog)
    recent_titles = existing_titles[-25:]
    backlog_tail = full_backlog[-1200:] if len(full_backlog) > 1200 else full_backlog

    files = scout.list_repo_files(repo_dir=repo_dir, limit=40)
    scope_section = (
        f"\nPROJECT SCOPE BOUNDARIES (STRICTLY ENFORCE):\n{scope}\n"
        if scope else ""
    )
    status_section = f"\nPROJECT STATUS:\n{status_summary}\n" if status_summary else ""
    files_section = (
        "\nEXISTING REPOSITORY FILES (via git ls-files):\n"
        + "\n".join(f"- {path}" for path in files)
        + "\n"
        if files else ""
    )
    existing_section = (
        "\nEXISTING BACKLOG TITLES (DO NOT DUPLICATE):\n"
        + "\n".join(f"- {title}" for title in recent_titles)
        + "\n"
        if recent_titles else ""
    )
    backlog_section = f"\nRECENT BACKLOG:\n{backlog_tail}\n" if backlog_tail else ""

    return f"""You are the Project Manager (pm) persona.
Decompose the user objective into 1 to 3 minimal, atomic, verifiable vertical-slice tasks.
Start numbering new tasks at TASK-{next_num:02d}.
Strictly obey PROJECT SCOPE BOUNDARIES, reference real paths from EXISTING REPOSITORY FILES (or allowed new modules/tests), and do NOT duplicate EXISTING BACKLOG TITLES.

USER OBJECTIVE:
{objective.strip()}
{status_section}{scope_section}{files_section}{existing_section}{backlog_section}
Respond ONLY with 1-3 markdown tasks in this exact format:
- [ ] **TASK-{next_num:02d}: <Title>**
  - **Goal:** <Goal in 1 sentence>
  - **Files:** <Exact target files>
  - **Criteria:** <Deterministic command/test verification exiting 0>
"""


def _assign_task_id(block_text: str, new_id: str) -> str:
    """Replace the TASK-XX identifier in a task block header line."""
    lines = block_text.splitlines()
    if not lines:
        return block_text
    lines[0] = re.sub(
        r"^(- \[ \] \*\*)TASK-[0-9A-Z-]+(:?\s*)",
        rf"\1{new_id}\2",
        lines[0],
        count=1,
    )
    return "\n".join(lines)


def sanitize_decomposed_tasks(
    raw_output: str,
    backlog_text: str = "",
    max_tasks: int = 3,
) -> list[str]:
    """Filter, deduplicate against backlog, normalize IDs, and cap at 1-3 task blocks."""
    blocks = scout.extract_task_blocks(raw_output or "")
    existing_ids = scout.extract_task_ids(backlog_text)
    existing_titles = scout.extract_all_backlog_titles(backlog_text)
    next_num = next_task_number(backlog_text)
    used_ids = set(existing_ids)

    accepted: list[str] = []
    for block in blocks:
        if scout.is_duplicate_title(block["title"], existing_titles):
            continue

        task_id = block["id"]
        num_match = re.match(r"^TASK-(\d+)$", task_id)
        if not num_match or task_id in used_ids:
            while f"TASK-{next_num:02d}" in used_ids:
                next_num += 1
            task_id = f"TASK-{next_num:02d}"
            text = _assign_task_id(block["text"], task_id)
            next_num += 1
        else:
            text = block["text"]
            next_num = max(next_num, int(num_match.group(1)) + 1)

        used_ids.add(task_id)
        existing_titles.append(block["title"])
        accepted.append(text)
        if len(accepted) >= max_tasks:
            break

    return accepted


def build_dry_run_task(
    objective: str,
    backlog_text: str = "",
    repo_dir: str = ".",
) -> str:
    """Build a deterministic offline preview TASK-XX block grounded in repo files."""
    clean_obj = " ".join(objective.strip().split()) or "Implement vertical slice task"
    task_num = next_task_number(backlog_text)
    files = scout.list_repo_files(repo_dir=repo_dir, limit=40)

    obj_tokens = scout.normalize_title_tokens(clean_obj)
    matched_files = [
        path for path in files
        if obj_tokens and any(tok in path.lower() for tok in obj_tokens)
    ]
    selected_files = (matched_files or files)[:2]
    files_str = ", ".join(selected_files) if selected_files else "BACKLOG.md"

    title = clean_obj[:80]
    return "\n".join([
        f"- [ ] **TASK-{task_num:02d}: {title}**",
        f"  - **Goal:** {clean_obj}",
        f"  - **Files:** {files_str}",
        "  - **Criteria:** .amase/test-gate.sh passes with exit code 0",
    ])


def decompose_objective(
    objective: str,
    backlog_path: str = "",
    scope_path: str = "",
    status_input: str = "",
    repo_dir: str = ".",
) -> str:
    """Query the free fleet with the pm persona and return sanitized 1-3 task blocks."""
    persona_path = os.path.join(ORCHESTRATOR_ROOT, "personas", "pm.md")
    pm_prompt = scout._read_slice(persona_path, max_chars=4000)
    user_prompt = build_decomposition_prompt(
        objective=objective,
        backlog_path=backlog_path,
        scope_path=scope_path,
        status_input=status_input,
        repo_dir=repo_dir,
    )

    t0 = time.time()
    try:
        content = query_fleet(
            user_prompt,
            system_prompt=pm_prompt,
            model_hint=MODEL,
            title="AMASE: Project Manager",
        )
        duration = int(time.time() - t0)
        usage = get_last_usage()
        try:
            record_telemetry(
                repo_dir,
                task_id="PLANNING",
                role="pm",
                model=usage.get("model") or MODEL,
                duration_seconds=duration,
                tokens_in=usage.get("tokens_in", 0),
                tokens_out=usage.get("tokens_out", 0),
                status="planned" if content else "empty",
            )
        except Exception:
            pass
        if not content:
            return ""
        backlog_text = scout._read_slice(backlog_path, max_chars=200000)
        tasks = sanitize_decomposed_tasks(content, backlog_text=backlog_text, max_tasks=3)
        return "\n\n".join(tasks)
    except Exception as exc:
        sys.stderr.write(f"PM decomposition failed: {exc}\n")
        return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AMASE Project Manager (pm) Requirement Decomposer"
    )
    parser.add_argument("positional_objective", nargs="?", help="User objective to decompose")
    parser.add_argument("--objective", help="User objective or feature request to decompose")
    parser.add_argument("--repo", default=os.getcwd(), help="Target repository directory")
    parser.add_argument("--backlog", default=None, help="Path to BACKLOG.md")
    parser.add_argument("--scope", default=None, help="Path to .amase/scope.md")
    parser.add_argument("--status", default="", help="Project status summary text or file path")
    parser.add_argument("--append", action="store_true", help="Append decomposed tasks to --backlog")
    parser.add_argument("--dry-run", action="store_true", help="Preview formatted TASK-XX block without LLM call or file writes")
    args = parser.parse_args(argv)

    repo_dir = os.path.abspath(args.repo)
    backlog_path = args.backlog or os.path.join(repo_dir, "BACKLOG.md")
    scope_path = args.scope or os.path.join(repo_dir, ".amase", "scope.md")
    objective = (args.objective or args.positional_objective or "").strip()

    if not objective and not args.dry_run:
        sys.stderr.write("Error: --objective is required unless --dry-run is specified.\n")
        return 2

    if args.dry_run:
        backlog_text = scout._read_slice(backlog_path, max_chars=200000)
        preview = build_dry_run_task(
            objective or "Sample vertical slice task",
            backlog_text=backlog_text,
            repo_dir=repo_dir,
        )
        print(preview)
        return 0

    output = decompose_objective(
        objective=objective,
        backlog_path=backlog_path,
        scope_path=scope_path,
        status_input=args.status,
        repo_dir=repo_dir,
    )
    if not output:
        sys.stderr.write("[-] Project Manager failed to generate valid tasks.\n")
        return 1

    print(output)
    if args.append and backlog_path:
        with open(backlog_path, "a") as f:
            f.write(f"\n{output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
