#!/usr/bin/env python3
"""
AMASE Real-Time Telemetry CLI Summary (amase stats)

Reads target_dir/.amase/telemetry.jsonl and prints formatted terminal tables:
1. Multi-Persona Activity Log (TIMESTAMP, ROLE, TASK_ID, MODEL, TOKENS, DURATION, COST)
2. Role Breakdown Summary (Builder, Sentinel, Scout, Coordinator totals)
"""

import json
import os
import sys
from pathlib import Path


def format_duration(seconds):
    """Format duration in seconds into human-readable string."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    mins = seconds // 60
    secs = seconds % 60
    if mins < 60:
        return f"{mins}m {secs}s"
    hours = mins // 60
    rem_mins = mins % 60
    return f"{hours}h {rem_mins}m"


def format_table_rows(entries):
    """Format telemetry entries into activity rows."""
    rows = []
    for entry in entries:
        timestamp = entry.get("timestamp", "N/A")
        # Strip milliseconds or timezone noise if long
        if "T" in timestamp:
            timestamp = timestamp.split(".")[0]
        role = entry.get("role", "builder")
        task_id = entry.get("task_id", "N/A")
        model = entry.get("model", "N/A")
        duration = entry.get("duration_seconds", 0)
        tokens_in = entry.get("tokens_in", 0)
        tokens_out = entry.get("tokens_out", 0)
        tokens_str = f"{tokens_in:,} / {tokens_out:,}" if (tokens_in or tokens_out) else "N/A"
        commit = entry.get("commit_hash", "")[:8] if entry.get("commit_hash") else ""
        cost = entry.get("cost_usd", 0.00)
        rows.append((timestamp, role, task_id, model, tokens_str, duration, commit, cost))
    return rows


def compute_role_summary(entries):
    """Compute aggregated summary grouped by role."""
    roles = {}
    for entry in entries:
        role = entry.get("role", "builder")
        if role not in roles:
            roles[role] = {
                "runs": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "duration": 0,
                "cost": 0.0,
            }
        roles[role]["runs"] += 1
        roles[role]["tokens_in"] += entry.get("tokens_in", 0)
        roles[role]["tokens_out"] += entry.get("tokens_out", 0)
        roles[role]["duration"] += entry.get("duration_seconds", 0)
        roles[role]["cost"] += entry.get("cost_usd", 0.0)
    return roles


def print_tables(rows, roles_summary):
    """Print the formatted activity table and role breakdown table."""
    if not rows:
        print("[-] No telemetry entries found.")
        print("  Run 'amase init' and complete tasks to generate telemetry.")
        return

    # Table 1: Activity Log
    width = 112
    sep = "+" + "-" * width + "+"
    print(sep)
    print(
        "| " + "{:<19}".format("TIMESTAMP")
        + "| " + "{:<10}".format("ROLE")
        + "| " + "{:<12}".format("TASK_ID")
        + "| " + "{:<28}".format("MODEL")
        + "| " + "{:<18}".format("TOKENS (IN/OUT)")
        + "| " + "{:<10}".format("DURATION")
        + "| " + "{:<8}".format("COST")
        + "|"
    )
    print(sep)

    for row in rows:
        timestamp, role, task_id, model, tokens_str, duration, commit, cost = row
        dur_str = format_duration(duration)
        cost_str = f"${cost:.2f}"
        print(
            "| " + "{:<19}".format(str(timestamp)[:19])
            + "| " + "{:<10}".format(str(role)[:10])
            + "| " + "{:<12}".format(str(task_id)[:12])
            + "| " + "{:<28}".format(str(model)[:28])
            + "| " + "{:<18}".format(str(tokens_str)[:18])
            + "| " + "{:<10}".format(str(dur_str)[:10])
            + "| " + "{:<8}".format(str(cost_str)[:8])
            + "|"
        )

    print(sep)
    print()

    # Table 2: Role Breakdown Summary
    summary_width = 88
    sum_sep = "+" + "-" * summary_width + "+"
    print(sum_sep)
    print(
        "| " + "{:<12}".format("ROLE")
        + "| " + "{:<6}".format("RUNS")
        + "| " + "{:<14}".format("TOKENS IN")
        + "| " + "{:<14}".format("TOKENS OUT")
        + "| " + "{:<14}".format("TOTAL TOKENS")
        + "| " + "{:<12}".format("DURATION")
        + "| " + "{:<8}".format("COST")
        + "|"
    )
    print(sum_sep)

    total_runs = 0
    total_tin = 0
    total_tout = 0
    total_dur = 0
    total_cost = 0.0

    # Sort roles predictably: builder, sentinel, scout, others
    ordered_roles = sorted(roles_summary.keys(), key=lambda r: ("builder", "sentinel", "scout").index(r) if r in ("builder", "sentinel", "scout") else 99)

    for role in ordered_roles:
        st = roles_summary[role]
        runs = st["runs"]
        tin = st["tokens_in"]
        tout = st["tokens_out"]
        ttot = tin + tout
        dur = st["duration"]
        cost = st["cost"]

        total_runs += runs
        total_tin += tin
        total_tout += tout
        total_dur += dur
        total_cost += cost

        print(
            "| " + "{:<12}".format(str(role).capitalize()[:12])
            + "| " + "{:<6}".format(f"{runs}")
            + "| " + "{:<14}".format(f"{tin:,}")
            + "| " + "{:<14}".format(f"{tout:,}")
            + "| " + "{:<14}".format(f"{ttot:,}")
            + "| " + "{:<12}".format(format_duration(dur))
            + "| " + "{:<8}".format(f"${cost:.2f}")
            + "|"
        )

    print(sum_sep)
    # Total Footer
    print(
        "| " + "{:<12}".format("TOTAL")
        + "| " + "{:<6}".format(f"{total_runs}")
        + "| " + "{:<14}".format(f"{total_tin:,}")
        + "| " + "{:<14}".format(f"{total_tout:,}")
        + "| " + "{:<14}".format(f"{total_tin + total_tout:,}")
        + "| " + "{:<12}".format(format_duration(total_dur))
        + "| " + "{:<8}".format(f"${total_cost:.2f}")
        + "|"
    )
    print(sum_sep)


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    target_dir = os.path.abspath(target_dir)

    telemetry_path = os.path.join(target_dir, ".amase", "telemetry.jsonl")
    if not os.path.exists(telemetry_path):
        print(f"[-] No telemetry file found at: {telemetry_path}")
        print("  Run 'amase init' and complete tasks to generate telemetry.")
        sys.exit(1)

    # Auto-backfill zero-token entries if any exist
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import extract_tokens
        extract_tokens.backfill_telemetry(target_dir)
    except Exception:
        pass

    entries = []
    try:
        with open(telemetry_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
    except OSError as e:
        print(f"[-] Error reading telemetry file: {e}")
        sys.exit(1)

    rows = format_table_rows(entries)
    roles_summary = compute_role_summary(entries)
    print_tables(rows, roles_summary)


if __name__ == "__main__":
    main()
