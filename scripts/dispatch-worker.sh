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

# Read config from worktree
CONFIG_FILE="$WORKTREE/.amase/config.json"
MODEL_TIER="free"
BUILDER_VISIBLE_TAB=true
CONFIGURED_BUILDER_MODELS=()
if [ -f "$CONFIG_FILE" ]; then
  MODEL_TIER=$(jq -r '.model_tier // "free"' "$CONFIG_FILE" 2>/dev/null || echo "free")
  BUILDER_VISIBLE_TAB=$(jq -r '.ui.builder_visible_tab // true' "$CONFIG_FILE" 2>/dev/null || echo "true")
  while IFS= read -r line; do
    [[ -n "$line" ]] && CONFIGURED_BUILDER_MODELS+=("$line")
  done < <(jq -r '.persona_routing.builder[]?' "$CONFIG_FILE" 2>/dev/null || true)
fi

# If builder visible tab is disabled, run headless
if [[ "$BUILDER_VISIBLE_TAB" == "false" ]]; then
  USE_GUI_TAB=0
else
  USE_GUI_TAB="${AMASE_GUI_TAB:-1}"
fi

# Ordered $0 Free Fleet (best performers first)
if [ "${#CONFIGURED_BUILDER_MODELS[@]}" -gt 0 ]; then
  FLEET_MODELS=(
    "$REQUESTED_MODEL"
    "${CONFIGURED_BUILDER_MODELS[@]}"
    "opencode/nemotron-3.5-lightning-free"
    "opencode/beam-free"
  )
else
  FLEET_MODELS=(
    "$REQUESTED_MODEL"
    "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"
    "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b"
    "openrouter/openrouter/free"
    "opencode/nemotron-3.5-lightning-free"
    "opencode/beam-free"
    "opencode/deepseek-v4.1-flash-free"
    "opencode/flint-40b-free"
    "opencode/mimo-v2.6-flash-free"
  )
fi

# If pro tier, prepend pro models
if [[ "$MODEL_TIER" == "pro" ]]; then
  FLEET_MODELS=(
    "opencode/gemini-2.5-pro"
    "opencode/claude-3-5-sonnet"
    "${FLEET_MODELS[@]}"
  )
fi

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

OPENCODE_FREE_EXHAUSTED=0

for MODEL in "${MODELS[@]}"; do
  if [[ "$MODEL" == opencode/*-free && "$OPENCODE_FREE_EXHAUSTED" -eq 1 ]]; then
    echo "[-] Skipping $MODEL (OpenCode free pool quota exhausted)"
    continue
  fi

  echo "=========================================================="
  echo "[+] AMASE Worker starting model: $MODEL"
  echo "=========================================================="
  printf '{"task_id": "%s", "model": "%s", "start_time": %s}\n' "$(basename "$WORKTREE")" "$MODEL" "$(date +%s)" > "$WORKTREE/.amase-task-meta.json"

  PROMPT=$(cat "$WORKTREE/.amase-task-prompt.txt")
  
  timeout --kill-after=5s 120s "$OPENCODE_BIN" run --print-logs --model "$MODEL" --auto "$PROMPT" 2>&1 | tee "$LOG_FILE" &
  WORKER_PID=$!

  # Sub-watchdog: checks every 1s for quota error (<1s) or timeout
  SUB_ELAPSED=0
  while kill -0 "$WORKER_PID" 2>/dev/null; do
    if grep -q "Free usage limit reached" "$LOG_FILE" 2>/dev/null || \
       ( [ -f ~/.local/share/opencode/log/opencode.log ] && tail -n 10 ~/.local/share/opencode/log/opencode.log | grep -q "Free usage limit reached" ); then
      echo ""
      echo "[!] Free usage limit reached in provider log (<1s). Killing opencode immediately and failing over..."
      kill -9 "$WORKER_PID" 2>/dev/null || true
      OPENCODE_FREE_EXHAUSTED=1
      break
    fi
    sleep 1
    SUB_ELAPSED=$((SUB_ELAPSED + 1))
  done
  wait "$WORKER_PID" 2>/dev/null || true

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
: "${USE_GUI_TAB:=${AMASE_GUI_TAB:-1}}"
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

  if [ "$STALL_SECONDS" -ge 45 ]; then
    echo "[-] Model stall detected (no output for 45s). Forcing failover..."
    pkill -P $(pgrep -f "$WORKTREE/.amase-run.sh") opencode 2>/dev/null || true
    STALL_SECONDS=0
  fi

  # Real-time quota detection in outer watchdog
  if grep -q "Free usage limit reached" "$LOG_FILE" 2>/dev/null || \
     ( [ -f ~/.local/share/opencode/log/opencode.log ] && tail -n 10 ~/.local/share/opencode/log/opencode.log | grep -q "Free usage limit reached" ); then
    if pgrep -f "$WORKTREE/.amase-run.sh" >/dev/null 2>&1; then
      echo "[!] Free quota limit detected in provider log. Instant kill to force failover..."
      pkill -P $(pgrep -f "$WORKTREE/.amase-run.sh") opencode 2>/dev/null || true
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
