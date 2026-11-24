#!/usr/bin/env bash
# ==============================================================================
# AMASE Task Abort & Worktree Pruner
# Cleanly terminates running worker processes, unmounts worktree, and deletes branch.
# Usage: scripts/abort-task.sh --repo <repo_path> --task <task_id>
# ==============================================================================
set -euo pipefail

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
      if [[ -z "$TASK_ID" ]]; then
        TASK_ID="$1"
        shift
      else
        echo "Unknown argument: $1"
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$TARGET_REPO" ]]; then
  TARGET_REPO="$(pwd)"
fi

if [[ -z "$TASK_ID" ]]; then
  echo "Usage: $0 --repo <repo_path> --task <task_id>"
  exit 1
fi

WORKTREE_PATH="$TARGET_REPO/.worktrees/$TASK_ID"
BRANCH_NAME="feature/$TASK_ID"

echo "[+] Aborting task: $TASK_ID in $TARGET_REPO..."

# 1. Close worker terminal tab if registered
if [[ -f "$WORKTREE_PATH/.amase-tty" ]]; then
  WORKER_TTY=$(cat "$WORKTREE_PATH/.amase-tty" 2>/dev/null | sed 's|/dev/||' || true)
  if [[ -n "$WORKER_TTY" && "$WORKER_TTY" != "not a tty" ]]; then
    pkill -HUP -t "$WORKER_TTY" 2>/dev/null || true
  fi
fi

# 2. Terminate any running worker processes for this worktree gracefully, then force
pkill -TERM -f "$WORKTREE_PATH" 2>/dev/null || true
sleep 0.5
pkill -9 -f "$WORKTREE_PATH" 2>/dev/null || true

# 2. Unmount and delete worktree
if [[ -d "$WORKTREE_PATH" ]]; then
  echo "[+] Unmounting worktree $WORKTREE_PATH..."
  git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
  git -C "$TARGET_REPO" worktree prune >/dev/null 2>&1 || true
fi

# 3. Delete ephemeral branch if it exists
if git -C "$TARGET_REPO" show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  echo "[+] Deleting branch $BRANCH_NAME..."
  git -C "$TARGET_REPO" branch -D "$BRANCH_NAME" >/dev/null 2>&1 || true
fi

echo "[+] Task $TASK_ID cleanly aborted. Repository state clean."
exit 0
