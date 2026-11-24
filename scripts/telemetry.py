#!/usr/bin/env python3
"""
AMASE Telemetry Logger
Standardized recording of execution telemetry across all personas
(Builder, Sentinel, Scout, Coordinator).
"""
import os
import sys
import json
from datetime import datetime, timezone

def record(
    repo_dir: str,
    task_id: str,
    role: str = "builder",
    model: str = "unknown",
    duration_seconds: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    commit_hash: str = "",
    cost_usd: float = 0.0,
    status: str = "settled"
):
    telemetry_dir = os.path.join(repo_dir, ".amase")
    os.makedirs(telemetry_dir, exist_ok=True)
    telemetry_file = os.path.join(telemetry_dir, "telemetry.jsonl")

    entry = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "task_id": task_id,
        "role": role,
        "model": model,
        "duration_seconds": int(duration_seconds),
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "commit_hash": commit_hash[:12] if commit_hash else "",
        "cost_usd": float(cost_usd),
        "status": status,
    }

    with open(telemetry_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        repo = sys.argv[1]
        tid = sys.argv[2]
        r = sys.argv[3]
        m = sys.argv[4]
        dur = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        tin = int(sys.argv[6]) if len(sys.argv) > 6 else 0
        tout = int(sys.argv[7]) if len(sys.argv) > 7 else 0
        ch = sys.argv[8] if len(sys.argv) > 8 else ""
        cost = float(sys.argv[9]) if len(sys.argv) > 9 else 0.0
        st = sys.argv[10] if len(sys.argv) > 10 else "settled"
        record(repo, tid, role=r, model=m, duration_seconds=dur, tokens_in=tin, tokens_out=tout, commit_hash=ch, cost_usd=cost, status=st)
