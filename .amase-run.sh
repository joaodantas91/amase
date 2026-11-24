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
