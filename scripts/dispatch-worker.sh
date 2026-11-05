#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher (Active Polling, Watchdog & Auto-Failover)
# - Detects model hang/stall: if no terminal output changes for 90s, auto-kills and fails over.
# - Detects completion: instant auto-settlement on commit or screen completion markers.
# ==============================================================================
set -euo pipefail

ORCA_BIN="/home/joao/.config/orca/linux-orca-cli-shim/orca"
WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"
REQUESTED_MODEL="${3:-mimo-v2.6-flash-free}"

# Ordered failover fleet for Orca
FLEET_MODELS=(
  "$REQUESTED_MODEL"
  "mimo-v2.6-flash-free"
  "flint-40b-free"
  "beam-free"
  "crouton-alpha-free"
)

# Remove duplicates while preserving order
UNIQUE_FLEET=()
for m in "${FLEET_MODELS[@]}"; do
  [[ " ${UNIQUE_FLEET[*]} " =~ " ${m} " ]] || UNIQUE_FLEET+=("$m")
done

FULL_PROMPT="$TASK_PROMPT. When finished, commit changes with git, then immediately exit the session."

for MODEL in "${UNIQUE_FLEET[@]}"; do
  echo "========================================================"
  echo "[+] AMASE Worker Dispatch (Orca UI Native)"
  echo "[+] Worktree: $WORKTREE"
  echo "[+] Model:    $MODEL"
  echo "[+] Timestamp: $(date -Iseconds)"
  echo "========================================================"

  OUTPUT=$("$ORCA_BIN" agent launch --worktree "path:$WORKTREE" --agent opencode --model "$MODEL" --prompt "$FULL_PROMPT" 2>&1 || true)
  HANDLE=$(echo "$OUTPUT" | grep "^handle:" | awk '{print $2}')

  if [[ -z "$HANDLE" ]]; then
    echo "[-] Failed to launch model $MODEL in Orca. Falling over to next model..."
    continue
  fi

  echo "[+] Worker tab opened in Orca with handle: $HANDLE"
  echo "[+] Watchdog active (90s stall limit, 600s total)..."

  MAX_SECONDS=600
  ELAPSED=0
  STALL_SECONDS=0
  LAST_SCREEN_HASH=""

  while [ $ELAPSED -lt $MAX_SECONDS ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    STALL_SECONDS=$((STALL_SECONDS + 5))

    # 1. Check for fresh git commit
    LAST_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    if [ "$LAST_COMMIT_TIME" -gt 0 ] && [ $((CURRENT_TIME - LAST_COMMIT_TIME)) -le 20 ]; then
      echo "[+] Detected fresh commit in worktree ($((CURRENT_TIME - LAST_COMMIT_TIME))s ago). Worker task completed!"
      "$ORCA_BIN" terminal close --terminal "$HANDLE" 2>/dev/null || true
      exit 0
    fi

    # 2. Check terminal screen content
    OUTPUT_TEXT=$("$ORCA_BIN" terminal read --terminal "$HANDLE" 2>/dev/null || true)
    CURRENT_HASH=$(echo "$OUTPUT_TEXT" | md5sum | awk '{print $1}')

    # Reset stall counter if screen changed
    if [ "$CURRENT_HASH" != "$LAST_SCREEN_HASH" ]; then
      LAST_SCREEN_HASH="$CURRENT_HASH"
      STALL_SECONDS=0
    fi

    # Check completion markers
    if echo "$OUTPUT_TEXT" | grep -qE "(Committed as [a-f0-9]+|Done\. All|Per system prompt, I did not commit|No new errors or failures introduced)"; then
      echo "[+] Detected completion markers in terminal output. Worker task completed!"
      "$ORCA_BIN" terminal close --terminal "$HANDLE" 2>/dev/null || true
      exit 0
    fi

    # 3. Watchdog: if stalled (no output change for 90s)
    if [ $STALL_SECONDS -ge 90 ]; then
      echo "[-] Watchdog: Terminal $HANDLE stalled with no output for 90s. Killing and failing over..."
      "$ORCA_BIN" terminal close --terminal "$HANDLE" 2>/dev/null || true
      break
    fi
  done
done

echo "[-] All fleet models exhausted or timed out."
exit 1
