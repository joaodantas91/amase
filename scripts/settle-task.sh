#!/usr/bin/env bash
# ==============================================================================
# AMASE Deterministic One-Click Settlement Script
# Verifies a task worktree (test gate + forbidden-file audit), merges
# feature/<task_id> into main, marks the task [x] in BACKLOG.md, and prunes
# the worktree.
# ==============================================================================
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  echo "Usage: $0 --repo <path> --task <task_id>"
  echo "Example: $0 --repo /home/joao/dev/orchestrator --task TASK-01"
  exit 1
}

TARGET_REPO=""
TASK_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      TARGET_REPO="$2"
      shift 2
      ;;
    --task)
      TASK_ID="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -z "$TARGET_REPO" || -z "$TASK_ID" ]]; then
  usage
fi

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "[-] Error: $TARGET_REPO is not a git repository."
  exit 1
fi

BRANCH_NAME="feature/$TASK_ID"
WORKTREE_PATH="$TARGET_REPO/.worktrees/$TASK_ID"
BACKLOG_FILE="$TARGET_REPO/BACKLOG.md"
AUDIT_FILE="$TARGET_REPO/AUDIT.md"
PTYXIS_BIN='/usr/bin/ptyxis'

echo "========================================================"
echo " AMASE Deterministic One-Click Settlement"
echo " Target Repo: $TARGET_REPO"
echo " Task ID:     $TASK_ID"
echo " Branch:      $BRANCH_NAME"
echo " Worktree:    $WORKTREE_PATH"
echo "========================================================"

# Read task metadata for telemetry ledger (before worktree is pruned).
META_FILE="$WORKTREE_PATH/.amase-task-meta.json"
META_MODEL="unknown"
META_START="$(date +%s)"
if [[ -f "$META_FILE" ]]; then
  META_READ=$(python3 - "$META_FILE" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("model", "unknown"), d.get("start_time", 0))
except Exception:
    print("unknown", 0)
PY
)
  META_MODEL="${META_READ%% *}"
  META_START="${META_READ##* }"
fi
[[ -z "$META_MODEL" || "$META_MODEL" == "null" ]] && META_MODEL="unknown"
if ! [[ "$META_START" =~ ^[0-9]+$ ]] || [[ "$META_START" == "0" ]]; then
  META_START="$(date +%s)"
fi

# 1. Run .amase/test-gate.sh in the worktree. Exit 1 on failure.
if [[ ! -x "$WORKTREE_PATH/.amase/test-gate.sh" ]]; then
  echo "[-] Error: .amase/test-gate.sh not found or not executable in $WORKTREE_PATH"
  exit 1
fi
echo "[+] Running targeted test gate in worktree..."
(cd "$WORKTREE_PATH" && ./.amase/test-gate.sh --diff-only) || {
  echo "[-] Targeted test gate failed in worktree $WORKTREE_PATH"
  exit 1
}
echo "[+] Running full .amase/test-gate.sh in worktree..."
(cd "$WORKTREE_PATH" && ./.amase/test-gate.sh) || {
  echo "[-] Test gate failed in worktree $WORKTREE_PATH"
  exit 1
}
echo "[+] Test gate passed."

# 2. Audit git diff between main and HEAD (worktree branch) for changes and forbidden files.
echo "[+] Auditing git diff main..$BRANCH_NAME for changes and forbidden files/patterns..."
CHANGED_FILES=$(git -C "$TARGET_REPO" diff --name-only "main..$BRANCH_NAME" 2>/dev/null || true)
DIFF_CONTENT=$(git -C "$TARGET_REPO" diff "main..$BRANCH_NAME" 2>/dev/null || true)

if [[ -z "$CHANGED_FILES" ]]; then
  echo "[-] Settlement Error: No commits or changes found on $BRANCH_NAME. Nothing to settle."
  exit 1
fi

# Reject empty governance-only commits (e.g. only .amase-rules.md, .amase-task-meta.json, etc.)
SOURCE_CHANGES=$(echo "$CHANGED_FILES" | grep -vE '^\.amase/|^\.amase-|\.amase_|\.md$|telemetry\.jsonl' || true)
if [[ -z "$SOURCE_CHANGES" ]]; then
  echo "[-] Settlement Error: No functional source or test code changes found on $BRANCH_NAME."
  echo "[-] Only internal governance/metadata files were modified: $(echo $CHANGED_FILES | tr '\n' ' ')"
  echo "[-] Rejecting empty settlement. Worker must implement actual code changes."
  exit 1
fi

if echo "$CHANGED_FILES" | grep -qE '^\.amase/scope\.md$'; then
  echo "[-] Forbidden file changed: .amase/scope.md"
  exit 1
fi

if echo "$CHANGED_FILES" | grep -qE '^\.env'; then
  echo "[-] Forbidden file changed: .env cannot be committed to git."
  exit 1
fi

echo "[+] Diff audit clean ($CHANGED_FILES)."

# 3. Merge feature/<task_id> into main.
echo "[+] Merging $BRANCH_NAME into main..."
git -C "$TARGET_REPO" checkout main >/dev/null 2>&1
if ! git -C "$TARGET_REPO" merge --ff-only "$BRANCH_NAME" >/dev/null 2>&1; then
  echo "[-] Fast-forward merge failed; trying normal merge..."
  if ! git -C "$TARGET_REPO" merge "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "[-] Merge into main failed."
    exit 1
  fi
fi
echo "[+] Merged $BRANCH_NAME into main."

# --- Post-merge invariant violation check ---
echo "[+] Running post-merge invariant violation check..."
INV_DIFF="$DIFF_CONTENT"

INV_FOUND=0

# Check for raw hex colors in .svelte/.vue/css files
if echo "$CHANGED_FILES" | grep -qE '\.(svelte|vue|css|scss|html)' && echo "$INV_DIFF" | grep -E '^\+[^+]' | grep -qE '#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?'; then
  echo "[!] Invariant violation: raw hex color found in added UI styles."
  INV_FOUND=1
fi

# Check for 'as any' or '@ts-ignore' in .ts/.tsx files
if echo "$CHANGED_FILES" | grep -qE '\.(ts|tsx)' && echo "$INV_DIFF" | grep -E '^\+[^+]' | grep -qE "as any|@ts-ignore"; then
  echo "[!] Invariant violation: 'as any' or '@ts-ignore' found in added TypeScript code."
  INV_FOUND=1
fi

# Automated UI Validation Check when UI files are touched
UI_TOUCHED=$(echo "$CHANGED_FILES" | grep -E '\.(svelte|vue|css|scss|html|jsx|tsx)$|entrypoints/' || true)
if [[ -n "$UI_TOUCHED" ]]; then
  CONFIG_FILE="$TARGET_REPO/.amase/config.json"
  [[ ! -f "$CONFIG_FILE" ]] && CONFIG_FILE="$ORCHESTRATOR_DIR/.amase/config.json"
  TARGET_URL=$(jq -r '.ui.target_url // empty' "$CONFIG_FILE" 2>/dev/null || true)

  if [[ -z "$TARGET_URL" ]]; then
    for static_html in "$TARGET_REPO/.output/chrome-mv3/popup.html" "$TARGET_REPO/.output/chrome-mv3/options.html" "$TARGET_REPO/dist/index.html" "$TARGET_REPO/build/index.html"; do
      if [[ -f "$static_html" ]]; then
        TARGET_URL="file://$static_html"
        break
      fi
    done
  fi

  if [[ -n "$TARGET_URL" && -f "$ORCHESTRATOR_DIR/scripts/ui_validator.py" ]]; then
    echo "[+] UI files modified ($UI_TOUCHED). Running automated UI validation audit on $TARGET_URL..."
    UI_REPORT=$(python3 "$ORCHESTRATOR_DIR/scripts/ui_validator.py" "$TARGET_URL" 2>&1 || true)
    echo "$UI_REPORT"
    if echo "$UI_REPORT" | grep -q "\[UI FAIL\]"; then
      echo "[!] UI Validator detected layout or runtime violations."
      INV_FOUND=1
      if [[ -f "$AUDIT_FILE" ]]; then
        echo "---" >> "$AUDIT_FILE"
        echo "UI Automation Audit Violations:" >> "$AUDIT_FILE"
        echo "$UI_REPORT" >> "$AUDIT_FILE"
      fi
    fi
  fi
fi

if [[ "$INV_FOUND" -eq 1 ]]; then
  echo "[+] Prepending TASK-INV-01 to BACKLOG.md for remediation..."
  if [[ -f "$BACKLOG_FILE" ]]; then
    sed -i "1s/^/- [ ] **TASK-INV-01: Remediate invariant and UI violations**\n/" "$BACKLOG_FILE"
  fi
  # Write findings to AUDIT.md
  if [[ -f "$AUDIT_FILE" ]]; then
    echo "[+] Appending invariant violations to AUDIT.md..."
    echo "---" >> "$AUDIT_FILE"
    echo "Invariant violations detected post-merge:" >> "$AUDIT_FILE"
    if echo "$CHANGED_FILES" | grep -qE '\.(svelte|vue|css|scss|html)'; then
      echo "- Raw hex color found in UI styles." >> "$AUDIT_FILE"
    fi
    if echo "$CHANGED_FILES" | grep -qE '\.(ts|tsx)'; then
      echo "- 'as any' or '@ts-ignore' found in TypeScript code." >> "$AUDIT_FILE"
    fi
  fi
else
  echo "[+] Sentinel invariant check clean: no invariant violations detected."
fi

BACKLOG_FILE="$TARGET_REPO/BACKLOG.md"

# 4. Run sentinel security audit on the merged codebase.
echo "[+] Running sentinel security audit..."
AUDIT_FILE="$TARGET_REPO/AUDIT.md"

# Check if sentinel_visible_tab is enabled in config
SENTINEL_VISIBLE=$(jq -r '.ui.sentinel_visible_tab // false' "$ORCHESTRATOR_DIR/.amase/config.json" 2>/dev/null || echo "false")

# Universal Terminal Discovery
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

if [[ "$SENTINEL_VISIBLE" == "true" ]] && [[ -n "$TERMINAL_BIN" ]] && [[ -n "${DISPLAY:-${WAYLAND_DISPLAY:-}}" ]]; then
  DONE_FLAG="$ORCHESTRATOR_DIR/.amase/sentinel_done"
  mkdir -p "$(dirname "$DONE_FLAG")"
  rm -f "$DONE_FLAG"

  SENTINEL_CMD="python3 '$ORCHESTRATOR_DIR/scripts/sentinel.py' '$TARGET_REPO' 2>&1 | tee '$AUDIT_FILE'; touch '$DONE_FLAG'; sleep 2"
  term_name=$(basename "$TERMINAL_BIN")
  case "$term_name" in
    ptyxis)
      if ! "$TERMINAL_BIN" --tab --working-directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" -- bash -c "$SENTINEL_CMD" 2>/dev/null; then
        "$TERMINAL_BIN" --new-window --working-directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" -- bash -c "$SENTINEL_CMD" &
      fi
      ;;
    gnome-terminal)
      "$TERMINAL_BIN" --tab --working-directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" -- bash -c "$SENTINEL_CMD" 2>/dev/null || \
      "$TERMINAL_BIN" --window --working-directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" -- bash -c "$SENTINEL_CMD" &
      ;;
    kitty)
      "$TERMINAL_BIN" --directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" bash -c "$SENTINEL_CMD" &
      ;;
    alacritty)
      "$TERMINAL_BIN" --working-directory="$TARGET_REPO" --title="AMASE: Sentinel Audit" -e bash -c "$SENTINEL_CMD" &
      ;;
    wezterm)
      "$TERMINAL_BIN" start --cwd "$TARGET_REPO" -- bash -c "$SENTINEL_CMD" &
      ;;
    konsole)
      "$TERMINAL_BIN" --workdir="$TARGET_REPO" -p "tabtitle=AMASE: Sentinel Audit" -e bash -c "$SENTINEL_CMD" &
      ;;
    *)
      bash -c "$SENTINEL_CMD" &
      ;;
  esac

  # Wait for DONE_FLAG (polling sleep 2, up to 300s)
  TIMEOUT=300
  ELAPSED=0
  while [[ $ELAPSED -lt $TIMEOUT ]]; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    [[ -f "$DONE_FLAG" ]] && break
  done
  rm -f "$DONE_FLAG"

  SENTINEL_OUTPUT=$(cat "$AUDIT_FILE" 2>/dev/null || true)
else
  SENTINEL_OUTPUT=$(python3 "$ORCHESTRATOR_DIR/scripts/sentinel.py" "$TARGET_REPO" 2>&1) || true
  echo "$SENTINEL_OUTPUT" > "$AUDIT_FILE"
fi

if echo "$SENTINEL_OUTPUT" | grep -qE '^[*-] \[(CRITICAL|HIGH)\]'; then
  echo "[!] Sentinel detected [CRITICAL] or [HIGH] vulnerability!"
  echo "[+] Prepending TASK-SEC-01 to BACKLOG.md for remediation..."
  if [[ -f "$BACKLOG_FILE" ]]; then
    sed -i "1s/^/- [ ] **TASK-SEC-01: Remediate Sentinel Audit Findings**\n/" "$BACKLOG_FILE"
  fi
else
  echo "[+] Sentinel audit clean: no critical/high vulnerabilities detected."
fi

# Commit AUDIT.md if it was created and contains output
if [[ -f "$AUDIT_FILE" ]] && [[ -s "$AUDIT_FILE" ]]; then
  echo "[+] Committing AUDIT.md..."
  git -C "$TARGET_REPO" add "$AUDIT_FILE"
  git -C "$TARGET_REPO" -c user.name="AMASE Settle" -c user.email="settle@amase.local" \
    commit -m "chore(settle): add sentinel audit output to AUDIT.md" >/dev/null 2>&1 || true
fi

# 5. Mark the task as [x] in BACKLOG.md and commit on main.
if [[ -f "$BACKLOG_FILE" ]]; then
  echo "[+] Marking $TASK_ID as [x] in BACKLOG.md..."
  sed -i "s/^\(- \[ \] \*\*$TASK_ID:\)/- [x] **$TASK_ID:/" "$BACKLOG_FILE"
  git -C "$TARGET_REPO" add "$BACKLOG_FILE"
  git -C "$TARGET_REPO" -c user.name="AMASE Settle" -c user.email="settle@amase.local" \
    commit -m "chore(settle): mark $TASK_ID as [x] in BACKLOG.md" >/dev/null 2>&1 || true
  echo "[+] BACKLOG.md updated."
else
  echo "[-] Warning: BACKLOG.md not found at $BACKLOG_FILE"
fi

# Extract token metrics (OpenCode SQLite database + heuristic fallback) before pruning
TOKENS_IN=0
TOKENS_OUT=0
if [[ -f "$ORCHESTRATOR_DIR/scripts/extract_tokens.py" ]]; then
  TOKEN_PAIR=$(python3 "$ORCHESTRATOR_DIR/scripts/extract_tokens.py" \
    --repo "$TARGET_REPO" \
    --task "$TASK_ID" \
    --worktree "$WORKTREE_PATH" \
    --start-time "$META_START" 2>/dev/null || echo "0 0")
  TOKENS_IN="${TOKEN_PAIR%% *}"
  TOKENS_OUT="${TOKEN_PAIR##* }"
fi
[[ -z "$TOKENS_IN" || ! "$TOKENS_IN" =~ ^[0-9]+$ || "$TOKENS_IN" -eq 0 ]] && TOKENS_IN=3500
[[ -z "$TOKENS_OUT" || ! "$TOKENS_OUT" =~ ^[0-9]+$ || "$TOKENS_OUT" -eq 0 ]] && TOKENS_OUT=450

# 5. Prune the worktree.
echo "[+] Pruning worktree $WORKTREE_PATH..."
git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
git -C "$TARGET_REPO" worktree prune >/dev/null 2>&1 || true
echo "[+] Worktree pruned."

# Record telemetry ledger entry.
echo "[+] Recording telemetry..."
CURRENT_TIME="$(date +%s)"
DURATION_SECONDS=$((CURRENT_TIME - META_START))
COMMIT_HASH="$(git -C "$TARGET_REPO" rev-parse HEAD)"

python3 "$ORCHESTRATOR_DIR/scripts/telemetry.py" "$TARGET_REPO" "$TASK_ID" "builder" "$META_MODEL" "$DURATION_SECONDS" "$TOKENS_IN" "$TOKENS_OUT" "$COMMIT_HASH" "0.00" "settled"
echo "[+] Telemetry recorded."

# Record successful task completion to flight recorder (~/.amase/retrospectives.jsonl)
python3 "$ORCHESTRATOR_DIR/scripts/diagnose-failure.py" "$TARGET_REPO" "$TASK_ID" "$META_MODEL" "" "$DURATION_SECONDS" "SUCCESS" 2>/dev/null || true

echo "========================================================"
echo "[+] Settlement complete for $TASK_ID."
echo "========================================================"
