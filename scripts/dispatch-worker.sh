#!/usr/bin/env bash
# ==============================================================================
# AMASE Worker Dispatcher (Single Dedicated Tab & Watchdog)
# - Opens EXACTLY ONE tab per task in Terminal (Ptyxis).
# - Handles model failovers internally in that single tab.
# - Auto-closes the tab upon task completion.
# - Polls for fresh git commit and settles automatically.
# ==============================================================================
set -euo pipefail

WORKTREE="${1:-}"
TASK_PROMPT="${2:-}"
REQUESTED_MODEL="${3:-opencode/nemotron-3.5-lightning-free}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt> [model]"
  exit 1
fi

OPENCODE_BIN="/home/joao/.bun/bin/opencode"
PTYXIS_BIN="/usr/bin/ptyxis"

# Ordered $0 Free Fleet (best performers first)
FLEET_MODELS=(
  "$REQUESTED_MODEL"
  "opencode/nemotron-3.5-lightning-free"
  "opencode/beam-free"
  "opencode/deepseek-v4.1-flash-free"
  "opencode/flint-40b-free"
  "opencode/mimo-v2.6-flash-free"
)

# Deduplicate
UNIQUE_FLEET=()
for m in "${FLEET_MODELS[@]}"; do
  [[ "$m" != opencode/* && "$m" != */* ]] && m="opencode/$m"
  [[ " ${UNIQUE_FLEET[*]} " =~ " ${m} " ]] || UNIQUE_FLEET+=("$m")
done

TASK_NAME=$(basename "$WORKTREE")
LOG_FILE="$WORKTREE/.amase-worker.log"
RUNNER_SCRIPT="$WORKTREE/.amase-run.sh"
DONE_FILE="$WORKTREE/.amase-done"

rm -f "$LOG_FILE" "$DONE_FILE"

INITIAL_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
START_TIME=$(date +%s)

# Generate single-tab runner script that loops through models in ONE terminal tab
cat > "$RUNNER_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -uo pipefail

WORKTREE="$1"
OPENCODE_BIN="$2"
LOG_FILE="$3"
DONE_FILE="$4"
INIT_COMMIT="$5"
shift 5
MODELS=("$@")

cd "$WORKTREE"

for MODEL in "${MODELS[@]}"; do
  echo "=========================================================="
  echo "[+] AMASE Worker starting model: $MODEL"
  echo "=========================================================="
  printf '{"task_id": "%s", "model": "%s", "start_time": %s}\n' "$(basename "$WORKTREE")" "$MODEL" "$(date +%s)" > "$WORKTREE/.amase-task-meta.json"

  PROMPT=$(cat "$WORKTREE/.amase-task-prompt.txt")
  
  "$OPENCODE_BIN" run --model "$MODEL" --auto "$PROMPT" 2>&1 | tee "$LOG_FILE" || true

  # If git commit made, we are done
  LAST_COMMIT=$(git log -1 --format="%ct" 2>/dev/null || echo 0)

  if [ "$LAST_COMMIT" -gt "$INIT_COMMIT" ]; then
    echo ""
    echo "[+] Task completed successfully by $MODEL!"
    touch "$DONE_FILE"
    echo "[+] Auto-closing tab in 2s..."
    sleep 2
    exit 0
  fi

  echo "[-] Model $MODEL did not commit. Failing over to next fleet model..."
done

echo "[-] All fleet models exhausted."
touch "$WORKTREE/.amase-failed"
sleep 5
exit 1
EOF

chmod +x "$RUNNER_SCRIPT"
echo "$TASK_PROMPT. When finished, commit changes with git." > "$WORKTREE/.amase-task-prompt.txt"

echo "========================================================"
echo "[+] AMASE Worker Dispatch (Single Tab Mode)"
echo "[+] Worktree: $WORKTREE"
echo "[+] Models:   ${UNIQUE_FLEET[*]}"
echo "[+] Timestamp: $(date -Iseconds)"
echo "========================================================"

# Launch worker in dedicated visible Ptyxis tab by default
USE_GUI_TAB="${AMASE_GUI_TAB:-1}"
if [[ "$USE_GUI_TAB" == "1" && -x "$PTYXIS_BIN" && -n "${DISPLAY:-${WAYLAND_DISPLAY:-}}" ]]; then
  echo "[+] Opening single worker tab in Terminal (Ptyxis)..."
  "$PTYXIS_BIN" --tab --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -- \
    "$RUNNER_SCRIPT" "$WORKTREE" "$OPENCODE_BIN" "$LOG_FILE" "$DONE_FILE" "$INITIAL_COMMIT_TIME" "${UNIQUE_FLEET[@]}" &
else
  echo "[+] Running worker in clean headless background (zero tab popups)..."
  "$RUNNER_SCRIPT" "$WORKTREE" "$OPENCODE_BIN" "$LOG_FILE" "$DONE_FILE" "$INITIAL_COMMIT_TIME" "${UNIQUE_FLEET[@]}" > "$LOG_FILE" 2>&1 &
fi

# Watchdog in coordinator session
MAX_SECONDS=600
ELAPSED=0
LAST_LOG_SIZE=0
STALL_SECONDS=0

while [ $ELAPSED -lt $MAX_SECONDS ]; do
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  STALL_SECONDS=$((STALL_SECONDS + 5))

  # 1. Check if git commit detected
  LAST_COMMIT_TIME=$(git -C "$WORKTREE" log -1 --format="%ct" 2>/dev/null || echo 0)
  if [ "$LAST_COMMIT_TIME" -gt "$INITIAL_COMMIT_TIME" ]; then
    CURRENT_TIME=$(date +%s)
    echo "[+] Detected fresh commit in worktree ($((CURRENT_TIME - LAST_COMMIT_TIME))s ago). Worker task completed!"
    # Wait up to 5s for runner to cleanly exit and close the tab
    for _ in {1..5}; do
      if [[ -f "$DONE_FILE" ]] || ! pgrep -f "$WORKTREE/.amase-run.sh" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    exit 0
  fi

  # 2. Check done flag
  if [[ -f "$DONE_FILE" ]]; then
    echo "[+] Worker reported completion. Settling..."
    sleep 1
    exit 0
  fi

  if [[ -f "$WORKTREE/.amase-failed" ]]; then
    echo "[-] Worker reported all fleet models failed."
    exit 1
  fi

  # Track log activity for heartbeat
  if [[ -f "$LOG_FILE" ]]; then
    CURRENT_LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$CURRENT_LOG_SIZE" -gt "$LAST_LOG_SIZE" ]; then
      LAST_LOG_SIZE="$CURRENT_LOG_SIZE"
      STALL_SECONDS=0
    fi
  fi

  if [ $((ELAPSED % 15)) -eq 0 ]; then
    LAST_LINE="..."
    if [[ -f "$LOG_FILE" ]]; then
      LAST_LINE=$(grep -v "^$" "$LOG_FILE" 2>/dev/null | tail -n 1 | head -c 80 || echo "...")
    fi
    echo "[Heartbeat] ${ELAPSED}s elapsed | Activity: $LAST_LINE"
  fi
done

echo "[-] Dispatcher timeout (600s reached)."
exit 1
