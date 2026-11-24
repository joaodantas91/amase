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
from datetime import datetime, timezone

def diagnose_log(log_path):
    """Analyze worker log content and return (signature, reason, metrics)."""
    if not os.path.exists(log_path):
        return "SOCKET_STALL", "Log file not created (immediate crash).", {"files_read": 0}

    try:
        with open(log_path, "r", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return "UNKNOWN_ERROR", f"Could not read log file: {e}", {"files_read": 0}

    # Count file read events in opencode log format
    files_read = len(re.findall(r'(?:reading path|read_file|reading file|loading path=)', content, re.IGNORECASE))
    metrics = {"files_read": files_read, "log_bytes": len(content)}

    # 1. Quota / Rate limit check
    if re.search(r'(Free usage limit reached|rate_limit_exceeded|429 Too Many Requests|TPM: Limit|quota exceeded)', content, re.IGNORECASE):
        return "QUOTA_EXHAUSTED", "Provider rate limit or free tier quota exhausted.", metrics

    # 2. Socket stall check
    if "stall detected" in content.lower() or len(content.strip()) < 50:
        return "SOCKET_STALL", "Worker hung on network socket without emitting progress.", metrics

    # 3. Compiler / Test Gate errors
    if re.search(r'(error TS[0-9]+|SyntaxError:|AssertionError|FAILED tests/|Command failed with exit code)', content, re.IGNORECASE):
        return "COMPILER_ERROR", "Worker code changes failed syntax, type check, or test gate.", metrics

    # 4. Context bloat check
    if files_read >= 10:
        return "CONTEXT_BLOAT", f"Worker inspected {files_read} files without completing task.", metrics

    return "MODEL_ABORT", "Worker exited cleanly without producing a git commit.", metrics


def record_retrospective(repo_dir, task_id, model, signature, reason, metrics=None, duration_seconds=0):
    """Write post-mortem record to target repo's .amase/retrospectives.jsonl."""
    amase_dir = os.path.join(repo_dir, ".amase")
    os.makedirs(amase_dir, exist_ok=True)
    retro_file = os.path.join(amase_dir, "retrospectives.jsonl")

    entry = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "task_id": task_id,
        "model": model,
        "failure_signature": signature,
        "reason": reason,
        "metrics": metrics or {},
        "duration_seconds": int(duration_seconds),
    }

    with open(retro_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[FlightRecorder] Logged post-mortem for {task_id}: {signature} ({reason})")


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

    signature, reason, metrics = diagnose_log(log_path)
    record_retrospective(target_repo, task_id, model, signature, reason, metrics, duration)


if __name__ == "__main__":
    main()
