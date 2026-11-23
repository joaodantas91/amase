#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher (Native Desktop Terminal / Ptyxis & Watchdog)
# - Opens a dedicated tab in your native terminal (Ptyxis / GNOME Terminal).
# - Tab stays open after completion with logs visible (never vanishes).
# - Active polling detects fresh git commit and settles automatically.
# - Auto-failover across $0 Free Fleet if model hangs (>60s).
# ==============================================================================
set -euo pipefail

WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"
REQUESTED_MODEL="${3:-opencode/mimo-v2.6-flash-free}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt> [model]"
  exit 1
fi

OPENCODE_BIN="/home/joao/.bun/bin/opencode"
PTYXIS_BIN="/usr/bin/ptyxis"

# Ordered $0 Free Fleet
FLEET_MODELS=(
  "$REQUESTED_MODEL"
  "opencode/mimo-v2.6-flash-free"
  "opencode/flint-40b-free"
  "opencode/beam-free"
  "opencode/deepseek-v4.1-flash-free"
  "opencode/nemotron-3.5-lightning-free"
)

# Remove duplicates while preserving order
UNIQUE_FLEET=()
for m in "${FLEET_MODELS[@]}"; do
  # Normalize model name if prefix missing
  [[ "$m" != opencode/* && "$m" != */* ]] && m="opencode/$m"
  [[ " ${UNIQUE_FLEET[*]} " =~ " ${m} " ]] || UNIQUE_FLEET+=("$m")
done

FULL_PROMPT="$TASK_PROMPT. When finished, commit changes with git."

TASK_NAME=$(basename "$WORKTREE")
LOG_FILE="$WORKTREE/.amase-worker.log"
rm -f "$LOG_FILE"

for MODEL in "${UNIQUE_FLEET[@]}"; do
  echo "========================================================"
  echo "[+] AMASE Worker Dispatch (Native Terminal Tab)"
  echo "[+] Worktree: $WORKTREE"
  echo "[+] Model:    $MODEL"
  echo "[+] Timestamp: $(date -Iseconds)"
  echo "========================================================"

  # Write task metadata for telemetry ledger
  printf '{"task_id": "%s", "model": "%s", "start_time": %s}\n' "$TASK_NAME" "$MODEL" "$(date +%s)" > "$WORKTREE/.amase-task-meta.json"

  INITIAL_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
  CURRENT_PID=""

  # Check if desktop terminal (Ptyxis) is available
  if [[ -x "$PTYXIS_BIN" && -n "${DISPLAY:-${WAYLAND_DISPLAY:-}}" ]]; then
    echo "[+] Launching worker in a new tab in Terminal (Ptyxis)..."
    "$PTYXIS_BIN" --tab --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME ($MODEL)" -- \
      bash -c "cd '$WORKTREE' && echo '[+] Starting AMASE Worker on $MODEL...' && '$OPENCODE_BIN' run --model '$MODEL' --auto '$FULL_PROMPT' 2>&1 | tee '$LOG_FILE'; echo '[+] Task complete. Closing tab in 3s...'; sleep 3" &
    CURRENT_PID=$!
  else
    echo "[+] Launching worker in background process (headless)..."
    (cd "$WORKTREE" && "$OPENCODE_BIN" run --model "$MODEL" --auto "$FULL_PROMPT" > "$LOG_FILE" 2>&1) &
    CURRENT_PID=$!
  fi

  echo "[+] Watchdog active (polling every 5s, 60s stall limit, 240s total)..."

  MAX_SECONDS=240
  ELAPSED=0
  STALL_SECONDS=0
  LAST_LOG_SIZE=0

  while [ $ELAPSED -lt $MAX_SECONDS ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    STALL_SECONDS=$((STALL_SECONDS + 5))

    # 1. Check for fresh git commit in worktree (The only true proof of completion)
    LAST_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
    if [ "$LAST_COMMIT_TIME" -gt "$INITIAL_COMMIT_TIME" ]; then
      CURRENT_TIME=$(date +%s)
      echo "[+] Detected fresh commit in worktree ($((CURRENT_TIME - LAST_COMMIT_TIME))s ago). Worker task completed!"
      exit 0
    fi

    # 2. Check worker log activity to reset stall timer
    if [[ -f "$LOG_FILE" ]]; then
      CURRENT_LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
      if [ "$CURRENT_LOG_SIZE" -gt "$LAST_LOG_SIZE" ]; then
        LAST_LOG_SIZE="$CURRENT_LOG_SIZE"
        STALL_SECONDS=0
      fi
    fi

    # Heartbeat output every 15s
    if [ $((ELAPSED % 15)) -eq 0 ]; then
      LAST_LINE="..."
      if [[ -f "$LOG_FILE" ]]; then
        LAST_LINE=$(grep -v "^$" "$LOG_FILE" 2>/dev/null | tail -n 1 | head -c 80 || echo "...")
      fi
      echo "[Heartbeat] ${ELAPSED}s elapsed | Stall: ${STALL_SECONDS}s | Activity: $LAST_LINE"
    fi

    # 3. Watchdog: if stalled (no new output in log for 60s)
    if [ $STALL_SECONDS -ge 60 ]; then
      echo "[-] Watchdog: Worker stalled with no output for 60s on model $MODEL. Killing and failing over..."
      if [[ -n "$CURRENT_PID" ]]; then
        kill -9 "$CURRENT_PID" 2>/dev/null || true
      fi
      pkill -9 -f "opencode.*$MODEL" 2>/dev/null || true
      break
    fi
  done
done

echo "[-] All fleet models exhausted or timed out."
exit 1
