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
REQUESTED_MODEL="${3:-nvidia/nvidia/nemotron-3.5-lightning-30b-a3b}"

if [[ -z "$WORKTREE" || -z "$TASK_PROMPT" ]]; then
  echo "Usage: $0 <worktree-path> <prompt> [model]"
  exit 1
fi

OPENCODE_BIN="/home/joao/.bun/bin/opencode"
ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Universal Terminal Discovery (supports any Linux desktop environment)
TERMINAL_BIN=""
if [[ -n "${AMASE_TERMINAL:-}" ]] && command -v "$AMASE_TERMINAL" >/dev/null 2>&1; then
  TERMINAL_BIN=$(command -v "$AMASE_TERMINAL")
elif [[ -n "${TERMINAL:-}" ]] && command -v "$TERMINAL" >/dev/null 2>&1; then
  TERMINAL_BIN=$(command -v "$TERMINAL")
else
  for term in ptyxis gnome-terminal kitty alacritty wezterm konsole x-terminal-emulator xterm; do
    if command -v "$term" >/dev/null 2>&1; then
      TERMINAL_BIN=$(command -v "$term")
      break
    fi
  done
fi

# Read config from worktree
CONFIG_FILE="$WORKTREE/.amase/config.json"
MODEL_TIER="free"
BUILDER_VISIBLE_TAB=true
CONFIGURED_BUILDER_MODELS=()
if [ -f "$CONFIG_FILE" ]; then
  MODEL_TIER=$(jq -r '.model_tier // "free"' "$CONFIG_FILE" 2>/dev/null || echo "free")
  BUILDER_VISIBLE_TAB=$(jq -r 'if .ui.builder_visible_tab != null then .ui.builder_visible_tab else true end' "$CONFIG_FILE" 2>/dev/null || echo "true")
  while IFS= read -r line; do
    [[ -n "$line" ]] && CONFIGURED_BUILDER_MODELS+=("$line")
  done < <(jq -r '.persona_routing.builder[]?' "$CONFIG_FILE" 2>/dev/null || true)
fi

# If builder visible tab is disabled, non-interactive, or headless flag set, run headless
if [[ "$BUILDER_VISIBLE_TAB" == "false" || "${AMASE_GUI_TAB:-}" == "0" || ! -t 1 ]]; then
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

# Add active local Ollama models to worker candidate fleet only if explicitly enabled
ALLOW_LOCAL_LLM="false"
if [ -f "$CONFIG_FILE" ]; then
  ALLOW_LOCAL_LLM=$(jq -r '.allow_local_llm // .local_models // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
fi
if [[ "${AMASE_ALLOW_LOCAL_LLM:-0}" == "1" ]]; then
  ALLOW_LOCAL_LLM="true"
fi

if [[ "$ALLOW_LOCAL_LLM" == "true" ]] && curl -s -m 1 http://localhost:11434/api/tags >/dev/null 2>&1; then
  LOCAL_CODER=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"qwen2.5-coder:[^"]*"' | tr -d '"' | head -n 1 || true)
  if [[ -n "$LOCAL_CODER" ]]; then
    echo "[+] Local Ollama coder model detected ($LOCAL_CODER), appended as opt-in fallback"
    FLEET_MODELS+=("ollama/$LOCAL_CODER")
  fi
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

# Automatic Worktree & Process Cleanup Trap on Interrupt
cleanup_on_interrupt() {
  echo ""
  echo "[!] Worker dispatch interrupted. Cleaning up worker processes and worktree..."
  pkill -P $$ 2>/dev/null || true
  pkill -f "$WORKTREE/.amase-run.sh" 2>/dev/null || true
  local parent_dir
  parent_dir="$(cd "$WORKTREE/../.." 2>/dev/null && pwd || true)"
  "$ORCHESTRATOR_DIR/scripts/abort-task.sh" --repo "${parent_dir:-$(pwd)}" --task "$TASK_NAME" 2>/dev/null || true
  exit 130
}
trap cleanup_on_interrupt INT TERM

# Safe Environment Inheritance from parent repo if not already present
PARENT_REPO="$(cd "$WORKTREE/../.." 2>/dev/null && pwd || true)"
if [[ -n "$PARENT_REPO" && -f "$PARENT_REPO/.env" && ! -f "$WORKTREE/.env" ]]; then
  cp -n "$PARENT_REPO/.env" "$WORKTREE/.env" 2>/dev/null || true
  if ! grep -qE "^\.env" "$WORKTREE/.gitignore" 2>/dev/null; then
    echo -e "\n.env\n.env.*\n" >> "$WORKTREE/.gitignore"
  fi
fi

rm -f "$LOG_FILE" "$DONE_FILE"

# Auto-tune OpenCode SQLite database for high concurrency: WAL mode, 10s busy timeout, synchronous NORMAL
python3 -c "
import sqlite3, os, time
p = os.path.expanduser('~/.local/share/opencode/opencode.db')
if os.path.exists(p):
    for attempt in range(5):
        try:
            conn = sqlite3.connect(p, timeout=5.0)
            conn.execute('PRAGMA journal_mode = WAL;')
            conn.execute('PRAGMA busy_timeout = 10000;')
            conn.execute('PRAGMA synchronous = NORMAL;')
            conn.close()
            break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() or 'busy' in str(e).lower():
                time.sleep(0.2 * (2 ** attempt))
            else:
                break
        except Exception:
            break
" 2>/dev/null || true

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
ORCHESTRATOR_DIR="$6"
shift 6
MODELS=("$@")

cd "$WORKTREE"
tty > "$WORKTREE/.amase-tty" 2>/dev/null || true

PREV_FAIL_ERROR=""

for MODEL in "${MODELS[@]}"; do

  # Check cross-worker persistent quota cooldown cache
  if [[ -f "$ORCHESTRATOR_DIR/scripts/quota_manager.py" ]]; then
    if ! python3 "$ORCHESTRATOR_DIR/scripts/quota_manager.py" --check "$MODEL" 2>/dev/null; then
      Q_MSG=$(python3 "$ORCHESTRATOR_DIR/scripts/quota_manager.py" --check "$MODEL" 2>&1 || true)
      echo "[-] Skipping $MODEL: $Q_MSG"
      continue
    fi
  fi

  echo "=========================================================="
  echo "[+] AMASE Worker starting model: $MODEL"
  echo "=========================================================="
  printf '{"task_id": "%s", "model": "%s", "start_time": %s}\n' "$(basename "$WORKTREE")" "$MODEL" "$(date +%s)" > "$WORKTREE/.amase-task-meta.json"

  PROMPT=$(cat "$WORKTREE/.amase-task-prompt.txt")
  if [[ -n "$PREV_FAIL_ERROR" ]]; then
    PROMPT=$(printf "%s\n\n## PRIORITY ADAPTIVE HANDOFF (PREVIOUS MODEL FAILED):\n%s\nDo NOT repeat the error above. Resolve this specific failure and ensure all tests pass.\n" "$PROMPT" "$PREV_FAIL_ERROR")
  fi
  
  # Stagger OpenCode startup across concurrent workers to serialize SQLite session table initialization
  if command -v flock >/dev/null 2>&1; then
    (
      flock -x -w 5 200 || true
      sleep 0.5
    ) 200>/tmp/amase-opencode-startup.lock
  else
    sleep $(( (RANDOM % 15) / 10 ))
  fi

  GLOBAL_OP_LOG="$HOME/.local/share/opencode/log/opencode.log"
  INIT_GLOBAL_OFFSET=0
  if [[ -f "$GLOBAL_OP_LOG" ]]; then
    INIT_GLOBAL_OFFSET=$(stat -c%s "$GLOBAL_OP_LOG" 2>/dev/null || echo 0)
  fi

  if command -v stdbuf >/dev/null 2>&1; then
    timeout --kill-after=5s 120s stdbuf -oL -eL "$OPENCODE_BIN" run --log-level WARN --print-logs --model "$MODEL" --auto "$PROMPT" 2>&1 | tee "$LOG_FILE" &
  else
    timeout --kill-after=5s 120s "$OPENCODE_BIN" run --log-level WARN --print-logs --model "$MODEL" --auto "$PROMPT" 2>&1 | tee "$LOG_FILE" &
  fi
  WORKER_PID=$!

  # Sub-watchdog: checks every 1s for quota error (<1s) or timeout
  SUB_ELAPSED=0
  while kill -0 "$WORKER_PID" 2>/dev/null; do
    QUOTA_HIT=0
    if grep -q "Free usage limit reached" "$LOG_FILE" 2>/dev/null; then
      QUOTA_HIT=1
    elif [[ -f "$GLOBAL_OP_LOG" ]]; then
      CURR_OFFSET=$(stat -c%s "$GLOBAL_OP_LOG" 2>/dev/null || echo 0)
      if [[ "$CURR_OFFSET" -gt "$INIT_GLOBAL_OFFSET" ]]; then
        if tail -c +$((INIT_GLOBAL_OFFSET + 1)) "$GLOBAL_OP_LOG" 2>/dev/null | grep -q "Free usage limit reached"; then
          QUOTA_HIT=1
        fi
      fi
    fi

    if [[ "$QUOTA_HIT" -eq 1 ]]; then
      echo ""
      echo "[!] Free usage limit reached in provider log for $MODEL. Failing over..."
      if [[ -f "$ORCHESTRATOR_DIR/scripts/quota_manager.py" ]]; then
        python3 "$ORCHESTRATOR_DIR/scripts/quota_manager.py" --record "$MODEL" --reason "Free usage limit reached" 2>/dev/null || true
      fi
      kill -9 "$WORKER_PID" 2>/dev/null || true
      break
    fi

    # SQLite busy or locked detection: back off and retry
    SQLITE_BUSY=0
    if grep -q "database is locked" "$LOG_FILE" 2>/dev/null; then
      SQLITE_BUSY=1
    elif [[ -f "$GLOBAL_OP_LOG" ]]; then
      CURR_OFFSET=$(stat -c%s "$GLOBAL_OP_LOG" 2>/dev/null || echo 0)
      if [[ "$CURR_OFFSET" -gt "$INIT_GLOBAL_OFFSET" ]]; then
        if tail -c +$((INIT_GLOBAL_OFFSET + 1)) "$GLOBAL_OP_LOG" 2>/dev/null | grep -q "database is locked"; then
          SQLITE_BUSY=1
        fi
      fi
    fi

    if [[ "$SQLITE_BUSY" -eq 1 ]]; then
      echo ""
      echo "[!] SQLite busy detected in provider log. Retrying with backoff..."
      kill -9 "$WORKER_PID" 2>/dev/null || true
      sleep 1
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
    echo "=========================================================="
    echo " [✓] TASK COMPLETED BY $MODEL"
    echo " [✓] Commit: $(git log -1 --oneline)"
    echo " [✓] Files changed:"
    git diff-tree --no-commit-id --name-status -r HEAD | sed 's/^/      /'
    echo "=========================================================="
    touch "$DONE_FILE"
    echo "[+] Auto-closing worker tab in 3s..."
    for i in 3 2 1; do
      echo "  $i..."
      sleep 1
    done
    exit 0
  fi

  # If worker made uncommitted changes in worktree that pass test-gate cleanly, verify they are REAL functional code changes
  REAL_CHANGES=$(git status --porcelain 2>/dev/null | grep -vE '^\?\?\s+\.amase|^\s*M\s+\.amase|\.amase_|telemetry\.jsonl' || true)
  if [[ -n "$REAL_CHANGES" ]]; then
    GATE_SCRIPT="$WORKTREE/.amase/test-gate.sh"
    if [[ -x "$GATE_SCRIPT" ]] && "$GATE_SCRIPT" >/dev/null 2>&1; then
      echo ""
      echo "=========================================================="
      echo " [+] Worker changes passed test gate cleanly!"
      echo " [+] Auto-committing on behalf of $MODEL..."
      git add -A
      git commit -m "feat($(basename "$WORKTREE")): completed by $MODEL"
      echo " [✓] Commit: $(git log -1 --oneline)"
      echo " [✓] Files changed:"
      git diff-tree --no-commit-id --name-status -r HEAD | sed 's/^/      /'
      echo "=========================================================="
      touch "$DONE_FILE"
      echo "[+] Auto-closing worker tab in 3s..."
      for i in 3 2 1; do
        echo "  $i..."
        sleep 1
      done
      exit 0
    fi
  fi

  echo "[-] Model $MODEL did not commit. Failing over to next fleet model..."

  # Capture failure excerpt for handoff to next candidate model
  PREV_FAIL_ERROR=""
  GATE_SCRIPT="$WORKTREE/.amase/test-gate.sh"
  if [[ -x "$GATE_SCRIPT" ]]; then
    RAW_GATE_OUT=$("$GATE_SCRIPT" 2>&1 || true)
    # Extract actual compiler/type/test failure diagnostics (file path, line, and Error message)
    DIAG_ERR=$(echo "$RAW_GATE_OUT" | grep -iE "error|fail|cannot find|not assignable|does not exist|\.ts:[0-9]+|\.js:[0-9]+" -B 1 -A 2 | tail -n 18 || true)
    if [[ -n "$DIAG_ERR" ]]; then
      PREV_FAIL_ERROR="Test gate diagnostics:\n$DIAG_ERR"
    else
      PREV_FAIL_ERROR="Test gate output:\n$(echo "$RAW_GATE_OUT" | tail -n 12)"
    fi
  fi
  if [[ -z "$PREV_FAIL_ERROR" && -f "$LOG_FILE" ]]; then
    LOG_ERR=$(grep -iE "error|fail|cannot find|not assignable|ts[0-9]+" "$LOG_FILE" 2>/dev/null | tail -n 10 || true)
    if [[ -n "$LOG_ERR" ]]; then
      PREV_FAIL_ERROR="Worker log error:\n$LOG_ERR"
    fi
  fi

  if grep -qi "Free usage limit reached\|rate_limit_exceeded\|insufficient_quota\|exceeded your current quota" "$LOG_FILE" 2>/dev/null; then
    if [[ -f "$ORCHESTRATOR_DIR/scripts/quota_manager.py" ]]; then
      python3 "$ORCHESTRATOR_DIR/scripts/quota_manager.py" --record "$MODEL" --reason "rate_limit_exceeded" 2>/dev/null || true
    fi
  fi
  python3 "$ORCHESTRATOR_DIR/scripts/diagnose-failure.py" "$WORKTREE" "$(basename "$WORKTREE")" "$MODEL" "$LOG_FILE" "$SUB_ELAPSED" 2>/dev/null || true
done

echo "[-] All fleet models exhausted."
python3 "$ORCHESTRATOR_DIR/scripts/diagnose-failure.py" "$WORKTREE" "$(basename "$WORKTREE")" "fleet-exhausted" "$LOG_FILE" 2>/dev/null || true
python3 "$ORCHESTRATOR_DIR/scripts/engine_incident.py" --record --script "scripts/dispatch-worker.sh" --signature "FLEET_EXHAUSTED" --message "All worker fleet models failed without producing a valid git commit for $(basename "$WORKTREE")" --project "$WORKTREE" 2>/dev/null || true
touch "$WORKTREE/.amase-failed"
echo "[-] Auto-closing failed worker tab in 2s..."
for i in 2 1; do
  echo "  $i..."
  sleep 1
done
exit 0
EOF

chmod +x "$RUNNER_SCRIPT"
echo "$TASK_PROMPT. When finished, commit changes with git." > "$WORKTREE/.amase-task-prompt.txt"

echo "========================================================"
echo "[+] AMASE Worker Dispatch (Single Tab Mode)"
echo "[+] Worktree: $WORKTREE"
echo "[+] Models:   ${UNIQUE_FLEET[*]}"
echo "[+] Timestamp: $(date -Iseconds)"
echo "========================================================"

launch_worker_ui() {
  local term_name
  term_name=$(basename "$TERMINAL_BIN")
  case "$term_name" in
    ptyxis)
      # Try tab in active window; if no active window, open in new window
      if ! "$TERMINAL_BIN" --tab --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -- "$RUNNER_SCRIPT" "$@" 2>/dev/null; then
        "$TERMINAL_BIN" --new-window --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -- "$RUNNER_SCRIPT" "$@" &
      fi
      ;;
    gnome-terminal)
      "$TERMINAL_BIN" --tab --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -- "$RUNNER_SCRIPT" "$@" 2>/dev/null || \
      "$TERMINAL_BIN" --window --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -- "$RUNNER_SCRIPT" "$@" &
      ;;
    kitty)
      "$TERMINAL_BIN" --directory="$WORKTREE" --title="AMASE: $TASK_NAME" "$RUNNER_SCRIPT" "$@" &
      ;;
    alacritty)
      "$TERMINAL_BIN" --working-directory="$WORKTREE" --title="AMASE: $TASK_NAME" -e "$RUNNER_SCRIPT" "$@" &
      ;;
    wezterm)
      "$TERMINAL_BIN" start --cwd "$WORKTREE" -- "$RUNNER_SCRIPT" "$@" &
      ;;
    konsole)
      "$TERMINAL_BIN" --workdir="$WORKTREE" -p "tabtitle=AMASE: $TASK_NAME" -e "$RUNNER_SCRIPT" "$@" &
      ;;
    x-terminal-emulator|xterm)
      "$TERMINAL_BIN" -T "AMASE: $TASK_NAME" -e "$RUNNER_SCRIPT" "$@" &
      ;;
    *)
      "$RUNNER_SCRIPT" "$@" > "$LOG_FILE" 2>&1 &
      ;;
  esac
}

# Launch worker in dedicated visible terminal window/tab by default
: "${USE_GUI_TAB:=${AMASE_GUI_TAB:-1}}"
if [[ ! -t 1 || "${AMASE_GUI_TAB:-}" == "0" ]]; then
  USE_GUI_TAB=0
fi
if [[ "$USE_GUI_TAB" == "1" && -n "$TERMINAL_BIN" && -n "${DISPLAY:-${WAYLAND_DISPLAY:-}}" ]]; then
  echo "[+] Opening visible worker tab/window in $(basename "$TERMINAL_BIN")..."
  launch_worker_ui "$WORKTREE" "$OPENCODE_BIN" "$LOG_FILE" "$DONE_FILE" "$INITIAL_COMMIT_TIME" "$ORCHESTRATOR_DIR" "${UNIQUE_FLEET[@]}"
else
  echo "[+] Running worker in clean headless background (zero tab popups)..."
  "$RUNNER_SCRIPT" "$WORKTREE" "$OPENCODE_BIN" "$LOG_FILE" "$DONE_FILE" "$INITIAL_COMMIT_TIME" "$ORCHESTRATOR_DIR" "${UNIQUE_FLEET[@]}" > "$LOG_FILE" 2>&1 &
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
    echo "[-] Worker reported all fleet models failed. Waiting for tab closure..."
    for _ in {1..3}; do
      if ! pgrep -f "$WORKTREE/.amase-run.sh" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    PARENT_REPO="$(cd "$WORKTREE/../.." 2>/dev/null && pwd || true)"
    "$ORCHESTRATOR_DIR/scripts/abort-task.sh" --repo "${PARENT_REPO:-$(pwd)}" --task "$TASK_NAME" 2>/dev/null || true
    exit 1
  fi

  # Track log activity for heartbeat across worker log and global opencode log
  ACTIVE_OUTPUT=0
  if [[ -f "$LOG_FILE" ]]; then
    CURRENT_LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$CURRENT_LOG_SIZE" -gt "$LAST_LOG_SIZE" ]; then
      LAST_LOG_SIZE="$CURRENT_LOG_SIZE"
      ACTIVE_OUTPUT=1
    fi
  fi
  GLOBAL_LOG="$HOME/.local/share/opencode/log/opencode.log"
  if [[ -f "$GLOBAL_LOG" ]]; then
    CURRENT_GLOBAL_SIZE=$(stat -c%s "$GLOBAL_LOG" 2>/dev/null || echo 0)
    if [ "$CURRENT_GLOBAL_SIZE" -gt "${LAST_GLOBAL_SIZE:-0}" ]; then
      LAST_GLOBAL_SIZE="$CURRENT_GLOBAL_SIZE"
      ACTIVE_OUTPUT=1
    fi
  fi
  if [ "$ACTIVE_OUTPUT" -eq 1 ]; then
    STALL_SECONDS=0
  fi

  if [ "$STALL_SECONDS" -ge 90 ]; then
    echo "[-] Model stall detected (no output or progress for 90s). Forcing failover..."
    pkill -P $(pgrep -f "$WORKTREE/.amase-run.sh") opencode 2>/dev/null || true
    STALL_SECONDS=0
  fi

  # Report model transitions and periodic heartbeat progress
  CURRENT_META_MODEL=""
  if [[ -f "$WORKTREE/.amase-task-meta.json" ]]; then
    CURRENT_META_MODEL=$(grep -o '"model": *"[^"]*"' "$WORKTREE/.amase-task-meta.json" 2>/dev/null | cut -d'"' -f4 || true)
  fi
  if [[ -n "$CURRENT_META_MODEL" && "$CURRENT_META_MODEL" != "${LAST_REPORTED_MODEL:-}" ]]; then
    echo "[+] Active worker model: $CURRENT_META_MODEL"
    LAST_REPORTED_MODEL="$CURRENT_META_MODEL"
  fi

  if [ $((ELAPSED % 15)) -eq 0 ]; then
    LAST_LINE="..."
    if [[ -f "$LOG_FILE" ]]; then
      LAST_LINE=$(grep -v "^$" "$LOG_FILE" 2>/dev/null | tail -n 1 | head -c 80 || echo "...")
    fi
    echo "[Heartbeat] ${ELAPSED}s elapsed (${CURRENT_META_MODEL:-worker}) | Activity: $LAST_LINE"
  fi
done

echo "[-] Dispatcher timeout (600s reached). Cleaning up worktree..."
PARENT_REPO="$(cd "$WORKTREE/../.." 2>/dev/null && pwd || true)"
"$ORCHESTRATOR_DIR/scripts/abort-task.sh" --repo "${PARENT_REPO:-$(pwd)}" --task "$TASK_NAME" 2>/dev/null || true
exit 1
