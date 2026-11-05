#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher (Orca Native Runner)
# Launches worker inside an interactive Orca UI Tab and waits for completion.
# ==============================================================================
set -euo pipefail

ORCA_BIN="/home/joao/.config/orca/linux-orca-cli-shim/orca"
WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"
MODEL="${3:-nemotron-3.5-lightning-free}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt> [model]" >&2
  exit 1
fi

if [[ ! -d "$WORKTREE" ]]; then
  echo "Error: Worktree directory $WORKTREE does not exist." >&2
  exit 1
fi

echo "========================================================"
echo "[+] AMASE Worker Dispatch (Orca UI Native)"
echo "[+] Worktree: $WORKTREE"
echo "[+] Model:    $MODEL"
echo "[+] Timestamp: $(date -Iseconds)"
echo "========================================================"

# Launch worker in Orca Tab
OUTPUT=$("$ORCA_BIN" agent launch --worktree "path:$WORKTREE" --agent opencode --model "$MODEL" --prompt "$TASK_PROMPT")
HANDLE=$(echo "$OUTPUT" | grep "^handle:" | awk '{print $2}')

if [[ -z "$HANDLE" ]]; then
  echo "[-] Failed to retrieve terminal handle from Orca output:"
  echo "$OUTPUT"
  exit 1
fi

echo "[+] Worker tab opened in Orca with handle: $HANDLE"
echo "[+] Waiting for worker completion in Orca..."

# Wait for Orca terminal to exit cleanly
"$ORCA_BIN" terminal wait --terminal "$HANDLE" --for exit --timeout-ms 300000

echo "[+] Worker terminal $HANDLE finished execution at $(date -Iseconds)"
exit 0
