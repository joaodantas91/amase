#!/usr/bin/env python3
"""
AMASE Parallel Worktree Dispatcher (amase parallel)

Analyzes pending tasks in BACKLOG.md, computes independent non-conflicting
task batches based on disjoint target file sets, and orchestrates concurrent
worker execution across isolated Git worktrees.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Add repo root to sys.path so scripts.fleet can be imported
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from scripts.fleet import get_sharded_model
except ImportError:
    try:
        from fleet import get_sharded_model
    except ImportError:
        def get_sharded_model(worker_index: int, total_workers: int = 2) -> str:
            shards = [
                "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b",
                "opencode/beam-free",
                "openrouter/openrouter/free"
            ]
            return shards[worker_index % len(shards)]



def parse_pending_tasks(backlog_path: str):
    """Parse pending [ ] tasks from BACKLOG.md extracting task_id, title, and target files."""
    if not os.path.isfile(backlog_path):
        return []

    with open(backlog_path, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r'^- \[ \] \*\*([A-Za-z0-9_-]+):?\s*([^*]*)\*\*\s*(.*)$', line)
        if match:
            task_id = match.group(1).strip()
            title = (match.group(2) + " " + match.group(3)).strip()
            files = []
            goal = ""
            criteria = ""
            i += 1

            while i < len(lines):
                sub = lines[i]
                if re.match(r'^\s{2}- \*\*', sub):
                    if "**Files:**" in sub:
                        raw_files = sub.split("**Files:**", 1)[1].strip()
                        # Extract files by splitting on commas, spaces, or backticks
                        for part in re.split(r'[,;\s]+', raw_files):
                            clean = part.strip("`'\",. ")
                            if clean and clean not in ("and", "&", "or"):
                                files.append(clean)
                    elif "**Goal:**" in sub:
                        goal = sub.split("**Goal:**", 1)[1].strip()
                    elif "**Criteria:**" in sub:
                        criteria = sub.split("**Criteria:**", 1)[1].strip()
                    i += 1
                elif sub.strip() == "":
                    i += 1
                else:
                    break

            tasks.append({
                "task_id": task_id,
                "title": title,
                "goal": goal,
                "files": list(set(files)),
                "criteria": criteria
            })
        else:
            i += 1

    return tasks


def have_file_conflicts(task_a, task_b) -> bool:
    """Return True if two tasks share any target files."""
    files_a = set(task_a.get("files", []))
    files_b = set(task_b.get("files", []))
    # If either task has no explicit files listed, assume potential conflict for safety
    if not files_a or not files_b:
        return True
    return bool(files_a.intersection(files_b))


def compute_non_conflicting_batches(tasks, max_parallel: int = 2):
    """Partition tasks into batches of mutually non-conflicting tasks."""
    batches = []
    for task in tasks:
        placed = False
        for batch in batches:
            if len(batch) < max_parallel:
                conflict = any(have_file_conflicts(task, existing) for existing in batch)
                if not conflict:
                    batch.append(task)
                    placed = True
                    break
        if not placed:
            batches.append([task])
    return batches


def execute_parallel_batch(repo_dir: str, batch: list):
    """Spawn worktrees and dispatch workers in parallel for a non-conflicting batch."""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    run_task_bin = os.path.join(scripts_dir, "run-task.sh")
    dispatch_worker_bin = os.path.join(scripts_dir, "dispatch-worker.sh")
    settle_task_bin = os.path.join(scripts_dir, "settle-task.sh")

    print(f"\n[+] Preparing parallel batch with {len(batch)} tasks...")
    worker_pids = []

    for idx, task in enumerate(batch):
        tid = task["task_id"]
        title = task["title"]
        shard_model = get_sharded_model(idx, len(batch))

        print(f"  [+] Provisioning worktree for {tid}...")
        prep_res = subprocess.run([run_task_bin, "--repo", repo_dir, "--task", tid], capture_output=True, text=True)
        if prep_res.returncode != 0:
            print(f"  [-] Failed to provision worktree for {tid}: {prep_res.stderr}")
            continue

        worktree_path = os.path.join(repo_dir, ".worktrees", tid)
        prompt = f"Implement task {tid}: {title}. Verify all tests pass. When finished, commit changes with git."

        print(f"  [+] Spawning worker for {tid} (Provider Shard: {shard_model})...")
        proc = subprocess.Popen([dispatch_worker_bin, worktree_path, prompt, shard_model])
        worker_pids.append((tid, worktree_path, proc, shard_model))

    print(f"\n[+] Waiting for {len(worker_pids)} parallel workers to finish...")
    for tid, wt_path, proc, shard_model in worker_pids:
        proc.wait()
        print(f"  [✓] Worker for {tid} finished with exit code {proc.returncode}.")

    # Deterministic sequential settlement (disjoint diffs merge cleanly)
    print("\n[+] Settling tasks sequentially...")
    for tid, wt_path, proc, shard_model in worker_pids:
        print(f"  [+] Settling {tid}...")
        res = subprocess.run([settle_task_bin, "--repo", repo_dir, "--task", tid])
        if res.returncode == 0:
            print(f"  [✓] {tid} settled successfully.")
        else:
            print(f"  [-] {tid} settlement failed.")


def main():
    parser = argparse.ArgumentParser(description="AMASE Parallel Worktree Dispatcher")
    parser.add_argument("--repo", default=".", help="Target repository directory")
    parser.add_argument("--backlog", default="", help="Path to BACKLOG.md")
    parser.add_argument("--max-parallel", type=int, default=2, help="Maximum concurrent workers per batch (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Print computed non-conflicting execution plan without running")

    args = parser.parse_args()
    repo_dir = os.path.abspath(args.repo)
    backlog_path = args.backlog or os.path.join(repo_dir, "BACKLOG.md")

    if not os.path.isfile(backlog_path):
        print(f"[-] Error: BACKLOG.md not found at {backlog_path}")
        sys.exit(1)

    pending_tasks = parse_pending_tasks(backlog_path)
    if not pending_tasks:
        print("[+] No pending [ ] tasks found in BACKLOG.md.")
        sys.exit(0)

    batches = compute_non_conflicting_batches(pending_tasks, max_parallel=args.max_parallel)

    print(f"\n========================================================")
    print(f" AMASE Parallel Execution Analysis")
    print(f" Target Repo:   {repo_dir}")
    print(f" Pending Tasks: {len(pending_tasks)}")
    print(f" Batches Found: {len(batches)}")
    print(f" Max Concurrency: {args.max_parallel}")
    print(f"========================================================\n")

    for i, batch in enumerate(batches, 1):
        concurrency = "Concurrent" if len(batch) > 1 else "Sequential"
        print(f"Batch {i} ({concurrency}, {len(batch)} task{'s' if len(batch) > 1 else ''}):")
        for idx, t in enumerate(batch):
            files_str = ", ".join(t['files']) if t['files'] else "(unspecified / broad scope)"
            shard_model = get_sharded_model(idx, len(batch))
            print(f"  [+] {t['task_id']}: {t['title']}")
            print(f"      Target Files:   {files_str}")
            print(f"      Provider Shard: {shard_model}")
        print()

    if args.dry_run:
        print("[+] Dry-run complete. Exiting without execution.")
        sys.exit(0)

    # Execute first batch
    first_batch = batches[0]
    execute_parallel_batch(repo_dir, first_batch)


if __name__ == "__main__":
    main()
