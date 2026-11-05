#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher
# Runs worker in background task with automatic reactive wakeup for coordinator.
# ==============================================================================
set -euo pipefail

WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt>" >&2
  exit 1
fi

if [[ ! -d "$WORKTREE" ]]; then
  echo "Error: Worktree directory $WORKTREE does not exist." >&2
  exit 1
fi

echo "========================================================"
echo "[+] AMASE Worker Dispatch"
echo "[+] Worktree: $WORKTREE"
echo "[+] Timestamp: $(date -Iseconds)"
echo "========================================================"

cd "$WORKTREE"

# Execute OpenCode worker with configured model
opencode run "$TASK_PROMPT"

EXIT_CODE=$?
echo "[+] Worker completed with exit code $EXIT_CODE at $(date -Iseconds)"
exit $EXIT_CODE
