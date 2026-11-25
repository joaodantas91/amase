#!/usr/bin/env python3
"""Structured Task Milestone Banner Script.

Renders compact, structured status cards at task start and
task completion/failure.

Usage:
    python3 scripts/task_banner.py --help
    python3 scripts/task_banner.py --task-start TASK_ID TITLE MODE WORKTREE BRANCH FILES_DURATION SECONDS_DURATION
    python3 scripts/task_banner.py --task-complete TASK_ID TITLE MODE WORKTREE BRANCH FILES_DURATION SECONDS_DURATION
    python3 scripts/task_banner.py --task-fail TASK_ID TITLE MODE WORKTREE BRANCH FILES_DURATION SECONDS_DURATION REASON
"""

import argparse
import sys


def _format_progress(done, total):
    pct = int((done / total) * 100) if total > 0 else 0
    return f"{done}/{total} ({pct}%)"


def _render_card(task_id, title, model, worktree, branch, files_modified, done, total, duration, reason="", status="start"):
    lines = []
    if status == "start":
        header = f"AMASE TASK BANNER - {task_id}"
        status_label = "STARTED"
    elif status == "complete":
        header = f"AMASE TASK BANNER - {task_id}"
        status_label = "COMPLETED"
    else:
        header = f"AMASE TASK BANNER - {task_id}"
        status_label = "FAILED"

    border = "━" * max(len(header), 40)

    lines.append(border)
    lines.append(header)
    lines.append(border)
    lines.append(f"ID:    {task_id}")
    lines.append(f"Title: {title}")
    lines.append(f"Model: {model}")
    lines.append(f"Worktree: {worktree}")
    lines.append(f"Branch: {branch}")
    lines.append(f"Files: {files_modified}")
    if duration:
        dur_str = str(duration)
        if isinstance(duration, (int, float)) and duration < 60:
            dur_str = f"{int(duration)}s"
        elif isinstance(duration, (int, float)):
            mins = int(duration // 60)
            secs = int(duration % 60)
            dur_str = f"{mins}:{secs:02d}m"
        lines.append(f"Duration: {dur_str}")
    else:
        lines.append("Duration: --")
    lines.append(f"Progress: {_format_progress(done, total)} | {total - done} pending")
    lines.append(f"Status: {status_label}")
    if status == "fail" and reason:
        lines.append(f"Reason: {reason}")
    lines.append(border)
    lines.append("")

    return "\n".join(lines)


def _banner(task_id, title, model, worktree, branch, files_modified, done, total, duration, status, reason=""):
    done = max(done, 0)
    total = max(total, 1)
    return _render_card(task_id, title, model, worktree, branch, files_modified, done, total, duration, reason, status)


def main():
    parser = argparse.ArgumentParser(
        description="Structured Task Milestone Banner Script",
    )
    parser.add_argument(
        "--task-start",
        nargs=6,
        metavar=("TASK_ID", "TITLE", "MODE", "WORKTREE", "BRANCH", "FILES_MODIFIED"),
        help="Render start banner",
    )
    parser.add_argument(
        "--task-complete",
        nargs=6,
        metavar=("TASK_ID", "TITLE", "MODE", "WORKTREE", "BRANCH", "FILES_MODIFIED"),
        help="Render completion banner",
    )
    parser.add_argument(
        "--task-fail",
        nargs=7,
        metavar=("TASK_ID", "TITLE", "MODE", "WORKTREE", "BRANCH", "FILES_MODIFIED", "REASON"),
        help="Render failure banner",
    )

    args = parser.parse_args()

    if args.task_start:
        task_id, title, model, worktree, branch, files_modified = args.task_start
        print(
            _banner(
                task_id=task_id,
                title=title,
                model=model,
                worktree=worktree,
                branch=branch,
                files_modified=files_modified,
                done=0,
                total=5,
                duration=0,
                status="start",
            )
        )
    elif args.task_complete:
        task_id, title, model, worktree, branch, files_modified = args.task_complete
        print(
            _banner(
                task_id=task_id,
                title=title,
                model=model,
                worktree=worktree,
                branch=branch,
                files_modified=files_modified,
                done=4,
                total=5,
                duration=125,
                status="complete",
            )
        )
    elif args.task_fail:
        task_id, title, model, worktree, branch, files_modified, reason = args.task_fail
        print(
            _banner(
                task_id=task_id,
                title=title,
                model=model,
                worktree=worktree,
                branch=branch,
                files_modified=files_modified,
                done=2,
                total=5,
                duration=60,
                status="fail",
                reason=reason,
            )
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()