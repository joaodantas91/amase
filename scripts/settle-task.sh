#!/usr/bin/env bash
# ==============================================================================
# AMASE Deterministic One-Click Settlement Script
# Verifies a task worktree (test gate + forbidden-file audit), merges
# feature/<task_id> into main, marks the task [x] in BACKLOG.md, and prunes
# the worktree.
# ==============================================================================
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  echo "Usage: $0 --repo <path> --task <task_id>"
  echo "Example: $0 --repo /home/joao/dev/orchestrator --task TASK-01"
  exit 1
}

TARGET_REPO=""
TASK_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      TARGET_REPO="$2"
      shift 2
      ;;
    --task)
      TASK_ID="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -z "$TARGET_REPO" || -z "$TASK_ID" ]]; then
  usage
fi

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "[-] Error: $TARGET_REPO is not a git repository."
  exit 1
fi

BRANCH_NAME="feature/$TASK_ID"
WORKTREE_PATH="$TARGET_REPO/.worktrees/$TASK_ID"

echo "========================================================"
echo " AMASE Deterministic One-Click Settlement"
echo " Target Repo: $TARGET_REPO"
echo " Task ID:     $TASK_ID"
echo " Branch:      $BRANCH_NAME"
echo " Worktree:    $WORKTREE_PATH"
echo "========================================================"

# Read task metadata for telemetry ledger (before worktree is pruned).
META_FILE="$WORKTREE_PATH/.amase-task-meta.json"
META_MODEL="unknown"
META_START="$(date +%s)"
if [[ -f "$META_FILE" ]]; then
  META_READ=$(python3 - "$META_FILE" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("model", "unknown"), d.get("start_time", 0))
except Exception:
    print("unknown", 0)
PY
)
  META_MODEL="${META_READ%% *}"
  META_START="${META_READ##* }"
fi
[[ -z "$META_MODEL" || "$META_MODEL" == "null" ]] && META_MODEL="unknown"
if ! [[ "$META_START" =~ ^[0-9]+$ ]] || [[ "$META_START" == "0" ]]; then
  META_START="$(date +%s)"
fi

# 1. Run .amase/test-gate.sh in the worktree. Exit 1 on failure.
if [[ ! -x "$WORKTREE_PATH/.amase/test-gate.sh" ]]; then
  echo "[-] Error: .amase/test-gate.sh not found or not executable in $WORKTREE_PATH"
  exit 1
fi
echo "[+] Running .amase/test-gate.sh in worktree..."
(cd "$WORKTREE_PATH" && ./.amase/test-gate.sh) || {
  echo "[-] Test gate failed in worktree $WORKTREE_PATH"
  exit 1
}
echo "[+] Test gate passed."

# 2. Audit git diff between main and HEAD (worktree branch) for changes and forbidden files.
echo "[+] Auditing git diff main..$BRANCH_NAME for changes and forbidden files/patterns..."
CHANGED_FILES=$(git -C "$TARGET_REPO" diff --name-only "main..$BRANCH_NAME" 2>/dev/null || true)
DIFF_CONTENT=$(git -C "$TARGET_REPO" diff "main..$BRANCH_NAME" 2>/dev/null || true)

if [[ -z "$CHANGED_FILES" ]]; then
  echo "[-] Settlement Error: No commits or changes found on $BRANCH_NAME. Nothing to settle."
  exit 1
fi

if echo "$CHANGED_FILES" | grep -qE '^\.amase/scope\.md$'; then
  echo "[-] Forbidden file changed: .amase/scope.md"
  exit 1
fi

TS_DIFF=$(git -C "$TARGET_REPO" diff "main..$BRANCH_NAME" -- '*.ts' '*.tsx' '*.js' '*.jsx' '*.svelte' 2>/dev/null || true)
if [[ -n "$TS_DIFF" ]] && echo "$TS_DIFF" | grep -qE "as any|@ts-ignore"; then
  echo "[-] Forbidden pattern found in TypeScript/JavaScript diff ('as any' or '@ts-ignore')"
  exit 1
fi

echo "[+] Diff audit clean ($CHANGED_FILES)."

# 3. Merge feature/<task_id> into main.
echo "[+] Merging $BRANCH_NAME into main..."
git -C "$TARGET_REPO" checkout main >/dev/null 2>&1
if ! git -C "$TARGET_REPO" merge --ff-only "$BRANCH_NAME" >/dev/null 2>&1; then
  echo "[-] Fast-forward merge failed; trying normal merge..."
  if ! git -C "$TARGET_REPO" merge "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "[-] Merge into main failed."
    exit 1
  fi
fi
echo "[+] Merged $BRANCH_NAME into main."

# 4. Mark the task as [x] in BACKLOG.md and commit on main.
BACKLOG_FILE="$TARGET_REPO/BACKLOG.md"
if [[ -f "$BACKLOG_FILE" ]]; then
  echo "[+] Marking $TASK_ID as [x] in BACKLOG.md..."
  sed -i "s/^\(- \[ \] \*\*$TASK_ID:\)/- [x] **$TASK_ID:/" "$BACKLOG_FILE"
  git -C "$TARGET_REPO" add "$BACKLOG_FILE"
  git -C "$TARGET_REPO" -c user.name="AMASE Settle" -c user.email="settle@amase.local" \
    commit -m "chore(settle): mark $TASK_ID as [x] in BACKLOG.md" >/dev/null 2>&1 || true
  echo "[+] BACKLOG.md updated."
else
  echo "[-] Warning: BACKLOG.md not found at $BACKLOG_FILE"
fi

# 5. Prune the worktree.
echo "[+] Pruning worktree $WORKTREE_PATH..."
git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
git -C "$TARGET_REPO" worktree prune >/dev/null 2>&1 || true
echo "[+] Worktree pruned."

# Record telemetry ledger entry.
echo "[+] Recording telemetry..."
CURRENT_TIME="$(date +%s)"
DURATION_SECONDS=$((CURRENT_TIME - META_START))
COMMIT_HASH="$(git -C "$TARGET_REPO" rev-parse HEAD)"
mkdir -p "$TARGET_REPO/.amase"
python3 - "$TARGET_REPO/.amase/telemetry.jsonl" "$(date -Iseconds)" "$TASK_ID" "$META_MODEL" "$DURATION_SECONDS" "$COMMIT_HASH" <<'PY'
import json, sys
path, ts, task_id, model, duration, commit_hash = sys.argv[1:7]
entry = {
    "timestamp": ts,
    "task_id": task_id,
    "model": model,
    "duration_seconds": int(duration),
    "commit_hash": commit_hash,
    "cost_usd": 0.00,
    "status": "settled",
}
with open(path, "a") as f:
    f.write(json.dumps(entry) + "\n")
PY
echo "[+] Telemetry recorded."

echo "========================================================"
echo "[+] Settlement complete for $TASK_ID."
echo "========================================================"
