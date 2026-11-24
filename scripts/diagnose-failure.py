#!/usr/bin/env python3
"""
AMASE Failure Diagnostic & Retrospective Flight Recorder
Analyzes failed worker run logs and classifies failures into machine-readable signatures:
- QUOTA_EXHAUSTED: Rate limits, free limits, or billing errors.
- SOCKET_STALL: Hung connection, zero bytes output, or sub-watchdog kill.
- COMPILER_ERROR: Test gate, syntax, or type check failures.
- CONTEXT_BLOAT: High file reading volume without commit progress.
- MODEL_ABORT: General exit without commit.
Appends post-mortem record to target_dir/.amase/retrospectives.jsonl.
"""
import os
import sys
import re
import json
import subprocess
from datetime import datetime, timezone

def diagnose_log(log_path, repo_dir=None):
    """Analyze worker log content and return (signature, reason, metrics)."""
    content = ""
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            content = f"Log read error: {e}"

    # If repo_dir has uncommitted changes that fail test gate, capture gate error
    test_gate_error = ""
    if repo_dir and os.path.isdir(repo_dir):
        gate_script = os.path.join(repo_dir, ".amase", "test-gate.sh")
        if os.path.exists(gate_script) and os.access(gate_script, os.X_OK):
            try:
                res = subprocess.run([gate_script], cwd=repo_dir, capture_output=True, text=True, timeout=15)
                if res.returncode != 0:
                    test_gate_error = (res.stderr or "") + "\n" + (res.stdout or "")
            except Exception:
                pass

    all_logs = content + "\n" + test_gate_error

    # Count file read events in opencode log format
    files_read = len(re.findall(r'(?:reading path|read_file|reading file|loading path=)', all_logs, re.IGNORECASE))
    metrics = {"files_read": files_read, "log_bytes": len(content)}

    # 1. Quota / Rate limit check
    if re.search(r'(Free usage limit reached|rate_limit_exceeded|429 Too Many Requests|TPM: Limit|quota exceeded)', all_logs, re.IGNORECASE):
        return "QUOTA_EXHAUSTED", "Provider rate limit or free tier quota exhausted.", metrics

    # 2. Socket stall check
    if "stall detected" in all_logs.lower() or (len(content.strip()) < 50 and not test_gate_error):
        return "SOCKET_STALL", "Worker hung on network socket without emitting progress.", metrics

    # 3. Compiler / Test Gate / Type Check errors
    compiler_pattern = (
        r'(error TS[0-9]+|SyntaxError:|AssertionError|FAILED tests/|Command failed with exit code|'
        r'svelte-check found [1-9]|Type .* is not assignable|No index signature|'
        r'Export declaration conflicts|Cannot find module|npm ERR!|ELIFECYCLE|'
        r'TypeScript error|TypeError:)'
    )
    if re.search(compiler_pattern, all_logs, re.IGNORECASE):
        return "COMPILER_ERROR", "Worker code changes failed syntax, type check, or test gate.", metrics

    # 4. Context bloat check
    if files_read >= 10:
        return "CONTEXT_BLOAT", f"Worker inspected {files_read} files without completing task.", metrics

    return "MODEL_ABORT", "Worker exited cleanly without producing a git commit.", metrics


def get_global_retro_path():
    """Return path to centralized worker flight recorder (~/.amase/retrospectives.jsonl)."""
    amase_home = os.path.expanduser("~/.amase")
    os.makedirs(amase_home, exist_ok=True)
    return os.path.join(amase_home, "retrospectives.jsonl")


def record_retrospective(repo_dir, task_id, model, signature, reason, metrics=None, duration_seconds=0):
    """Write post-mortem record to centralized flight recorder ~/.amase/retrospectives.jsonl."""
    retro_file = get_global_retro_path()
    entry = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "project": os.path.abspath(repo_dir),
        "project_name": os.path.basename(os.path.abspath(repo_dir)),
        "task_id": task_id,
        "model": model,
        "failure_signature": signature,
        "reason": reason,
        "metrics": metrics or {},
        "duration_seconds": int(duration_seconds),
    }

    with open(retro_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[FlightRecorder] Logged post-mortem for {task_id}: {signature} ({reason}) in {retro_file}")


def main():
    if len(sys.argv) < 4:
        print("Usage: diagnose-failure.py <worktree_or_repo> <task_id> <model> [log_path] [duration_seconds]")
        sys.exit(1)

    worktree = os.path.abspath(sys.argv[1])
    task_id = sys.argv[2]
    model = sys.argv[3]
    log_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(worktree, ".amase-worker.log")
    duration = int(sys.argv[5]) if len(sys.argv) > 5 else 0

    # Find the target git repo root (worktree parent or target)
    try:
        import subprocess
        res = subprocess.run(["git", "-C", worktree, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if res.returncode == 0:
            target_repo = res.stdout.strip()
            # If in worktree (.worktrees/TASK-XX), target is parent repo
            if ".worktrees" in target_repo:
                target_repo = os.path.abspath(os.path.join(target_repo, "..", ".."))
        else:
            target_repo = worktree
    except Exception:
        target_repo = worktree

    signature, reason, metrics = diagnose_log(log_path, repo_dir=worktree)
    record_retrospective(target_repo, task_id, model, signature, reason, metrics, duration)


if __name__ == "__main__":
    main()
