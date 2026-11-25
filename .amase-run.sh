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
    sleep 3
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
      sleep 3
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
sleep 2
exit 0
