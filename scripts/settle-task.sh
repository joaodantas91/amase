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

echo "========================================================"
echo " AMASE Deterministic One-Click Settlement"
echo " Target Repo: $TARGET_REPO"
echo " Task ID:     $TASK_ID"
echo " Branch:      $BRANCH_NAME"
echo " Worktree:    $WORKTREE_PATH"
echo "========================================================"

# 1. Run .amase/test-gate.sh in the worktree. Exit 1 on failure.
if [[ ! -x "$WORKTREE_PATH/.amase/test-gate.sh" ]]; then
  echo "[-] Error: .amase/test-gate.sh not found or not executable in $WORKTREE_PATH"
  exit 1
fi
echo "[+] Running .amase/test-gate.sh in worktree..."
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

if echo "$CHANGED_FILES" | grep -qE '^\.amase/scope\.md$'; then
  echo "[-] Forbidden file changed: .amase/scope.md"
  exit 1
fi

if echo "$DIFF_CONTENT" | grep -qE "as any|@ts-ignore"; then
  echo "[-] Forbidden pattern found in diff ('as any' or '@ts-ignore')"
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

# 4. Mark the task as [x] in BACKLOG.md and commit on main.
BACKLOG_FILE="$TARGET_REPO/BACKLOG.md"
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

# 5. Prune the worktree.
echo "[+] Pruning worktree $WORKTREE_PATH..."
git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
git -C "$TARGET_REPO" worktree prune >/dev/null 2>&1 || true
echo "[+] Worktree pruned."

echo "========================================================"
echo "[+] Settlement complete for $TASK_ID."
echo "========================================================"
