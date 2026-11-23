#!/usr/bin/env python3
"""
AMASE Real-Time Telemetry CLI Summary (amase stats)

Reads target_dir/.amase/telemetry.jsonl and prints a formatted terminal table
showing TIMESTAMP, TASK_ID, MODEL, DURATION, COMMIT, COST ($0.00),
with summary footer totals.
"""

import json
import os
import sys
from pathlib import Path


def format_table_rows(entries):
    """Format telemetry entries into table rows."""
    rows = []
    for entry in entries:
        timestamp = entry.get("timestamp", "N/A")
        task_id = entry.get("task_id", "N/A")
        model = entry.get("model", "N/A")
        duration = entry.get("duration_seconds", 0)
        commit = entry.get("commit_hash", "N/A")[:12] if entry.get("commit_hash") else "N/A"
        cost = entry.get("cost_usd", 0.00)
        rows.append((timestamp, task_id, model, duration, commit, cost))
    return rows


def compute_summary(entries):
    """Compute summary totals from telemetry entries."""
    count = len(entries)
    total_duration = sum(entry.get("duration_seconds", 0) for entry in entries)
    total_cost = sum(entry.get("cost_usd", 0.00) for entry in entries)
    return count, total_duration, total_cost


def print_table(rows, summary):
    """Print the formatted telemetry table."""
    if not rows:
        print("[-] No telemetry entries found.")
        print("  Run 'amase init' and complete tasks to generate telemetry.")
        return

    # Table header
    header = (
        "+" + "-" * 78 + "+"
        + "| " + "{:<20}".format("TIMESTAMP")
        + "| " + "{:<15}".format("TASK_ID")
        + "| " + "{:<20}".format("MODEL")
        + "| " + "{:<10}".format("DURATION")
        + "| " + "{:<12}".format("COMMIT")
        + "| " + "{:<10}".format("COST")
        + "|"
    )
    separator = "+" + "-" * 78 + "+"
    print(header)
    print(separator)

    for row in rows:
        timestamp, task_id, model, duration, commit, cost = row
        # Format duration as minutes/seconds if >= 60
        dur_str = f"{duration}s"
        if duration >= 60:
            mins = duration // 60
            secs = duration % 60
            dur_str = f"{mins}m {secs}s"
        # Format cost to 2 decimal places
        cost_str = f"${cost:.2f}"
        print(
            "| " + "{:<20}".format(str(timestamp))
            + "| " + "{:<15}".format(str(task_id))
            + "| " + "{:<20}".format(str(model))
            + "| " + "{:<10}".format(dur_str)
            + "| " + "{:<12}".format(commit)
            + "| " + "{:<10}".format(cost_str)
            + "|"
        )

    print(separator)

    # Summary footer
    count, total_duration, total_cost = summary
    if count == 1:
        print("| " + "{:<76}".format("TOTAL") + "| " + "{:<15}".format("") + "| " + "{:<20}".format("") + "| " + "{:<10}".format("") + "| " + "{:<12}".format("") + "| " + "{:<10}".format(f"${total_cost:.2f}") + "|")
    else:
        avg_duration = total_duration / count if count > 0 else 0
        print(
            "| " + "{:<76}".format("TOTAL")
            + "| " + "{:<15}".format(str(count))
            + "| " + "{:<20}".format("")
            + "| " + "{:<10}".format(f"{total_duration}s")
            + "| " + "{:<12}".format("")
            + "| " + "{:<10}".format(f"${total_cost:.2f}")
            + "|"
        )


def main():
    # Determine target directory (default to current working directory)
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    # Resolve to absolute path
    target_dir = os.path.abspath(target_dir)

    # Path to telemetry file
    telemetry_path = os.path.join(target_dir, ".amase", "telemetry.jsonl")

    # Check if telemetry file exists
    if not os.path.exists(telemetry_path):
        print(f"[-] No telemetry file found at: {telemetry_path}")
        print("  Run 'amase init' and complete tasks to generate telemetry.")
        sys.exit(1)

    # Read and parse telemetry entries
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
                        # Skip malformed lines
                        continue
    except OSError as e:
        print(f"[-] Error reading telemetry file: {e}")
        sys.exit(1)

    # Format and print table
    rows = format_table_rows(entries)
    summary = compute_summary(entries)
    print_table(rows, summary)


if __name__ == "__main__":
    main()