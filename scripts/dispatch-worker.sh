#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher (Active Polling & Auto-Settlement)
# Monitors Orca terminal output and detects completion immediately when worker finishes.
# ==============================================================================
set -euo pipefail

ORCA_BIN="/home/joao/.config/orca/linux-orca-cli-shim/orca"
WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"
MODEL="${3:-mimo-v2.6-flash-free}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt> [model]" >&2
  exit 1
fi

if [[ ! -d "$WORKTREE" ]]; then
  echo "Error: Worktree directory $WORKTREE does not exist." >&2
  exit 1
fi

# Append mandatory exit contract to prompt
FULL_PROMPT="$TASK_PROMPT. When finished, commit changes with git, then immediately exit the session."

echo "========================================================"
echo "[+] AMASE Worker Dispatch (Orca UI Native)"
echo "[+] Worktree: $WORKTREE"
echo "[+] Model:    $MODEL"
echo "[+] Timestamp: $(date -Iseconds)"
echo "========================================================"

OUTPUT=$("$ORCA_BIN" agent launch --worktree "path:$WORKTREE" --agent opencode --model "$MODEL" --prompt "$FULL_PROMPT")
HANDLE=$(echo "$OUTPUT" | grep "^handle:" | awk '{print $2}')

if [[ -z "$HANDLE" ]]; then
  echo "[-] Failed to retrieve terminal handle from Orca output:"
  echo "$OUTPUT"
  exit 1
fi

echo "[+] Worker tab opened in Orca with handle: $HANDLE"
echo "[+] Active polling for completion..."

MAX_SECONDS=600
ELAPSED=0

while [ $ELAPSED -lt $MAX_SECONDS ]; do
  sleep 5
  ELAPSED=$((ELAPSED + 5))

  # 1. Check if git commit was created in the worktree
  LAST_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
  CURRENT_TIME=$(date +%s)
  
  # If commit was created in the last 20 seconds, worker finished its work
  if [ "$LAST_COMMIT_TIME" -gt 0 ] && [ $((CURRENT_TIME - LAST_COMMIT_TIME)) -le 20 ]; then
    echo "[+] Detected fresh commit in worktree ($((CURRENT_TIME - LAST_COMMIT_TIME))s ago). Worker task completed!"
    "$ORCA_BIN" terminal close --terminal "$HANDLE" 2>/dev/null || true
    exit 0
  fi

  # 2. Check terminal screen content for completion signs
  OUTPUT_TEXT=$("$ORCA_BIN" terminal read --terminal "$HANDLE" 2>/dev/null || true)
  if echo "$OUTPUT_TEXT" | grep -qE "(Committed as [a-f0-9]+|Done\. All|Per system prompt, I did not commit|No new errors or failures introduced)"; then
    echo "[+] Detected completion markers in terminal output. Worker task completed!"
    "$ORCA_BIN" terminal close --terminal "$HANDLE" 2>/dev/null || true
    exit 0
  fi
done

echo "[-] Timeout reached without auto-settlement."
exit 1
