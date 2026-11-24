#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_REPO="${1:-$(pwd)}"
TASK_ID="TASK-TEST-WIRING"
BRANCH_NAME="feature/$TASK_ID"
WORKTREE_PATH="$TARGET_REPO/.worktrees/$TASK_ID"

echo "========================================================"
echo " AMASE Test-Wiring Simulator"
echo " Target Repo: $TARGET_REPO"
echo " Task ID:     $TASK_ID"
echo " Branch:      $BRANCH_NAME"
echo " Worktree:    $WORKTREE_PATH"
echo "========================================================"

# 0. Check writable filesystem in TARGET_REPO
if ! touch "$TARGET_REPO/.amase_write_test" 2>/dev/null; then
  echo "[-] ERROR: $TARGET_REPO is read-only in this session."
  exit 1
fi
rm -f "$TARGET_REPO/.amase_write_test"

# 1. Ensure .worktrees is ignored in the target repo
if ! grep -q "^\.worktrees" "$TARGET_REPO/.gitignore" 2>/dev/null; then
  echo -e "\n.worktrees/" >> "$TARGET_REPO/.gitignore"
  echo "[+] Added .worktrees/ to $TARGET_REPO/.gitignore"
fi

# 2. Cleanup existing worktree if stale
if [ -d "$WORKTREE_PATH" ]; then
  echo "[!] Worktree $WORKTREE_PATH already exists. Removing..."
  git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
fi

# 3. Create isolated ephemeral worktree
echo "[+] Creating Git worktree on branch $BRANCH_NAME..."
git -C "$TARGET_REPO" branch -D "$BRANCH_NAME" 2>/dev/null || true
mkdir -p "$(dirname "$WORKTREE_PATH")"
git -C "$TARGET_REPO" worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH"

# 4. Inject scoped agent directives & boundaries into worktree root
if [[ -x "$ORCHESTRATOR_DIR/scripts/generate-agent.sh" ]]; then
  "$ORCHESTRATOR_DIR/scripts/generate-agent.sh" --repo "$TARGET_REPO" --role builder --task "$TASK_ID" > "$WORKTREE_PATH/.amase-rules.md"
  echo "[+] Generated role-bounded builder directives with scope enforcement in .amase-rules.md"
else
  cat "$ORCHESTRATOR_DIR/prompts/swarm_invariants.md" \
      "$ORCHESTRATOR_DIR/prompts/design.md" \
      "$ORCHESTRATOR_DIR/prompts/ponytail.md" \
      "$ORCHESTRATOR_DIR/prompts/caveman.md" > "$WORKTREE_PATH/.amase-rules.md"
  echo "[+] Injected default agent directives into .amase-rules.md"
fi

# 5. Link or copy skills so child agents can access them directly
mkdir -p "$WORKTREE_PATH/.agents/skills"
cp -rn "$ORCHESTRATOR_DIR/skills/"* "$WORKTREE_PATH/.agents/skills/" 2>/dev/null || true
echo "[+] Injected skills into worktree."

# 6. Export LiteLLM Gateway Endpoint for worker agents
export OPENAI_BASE_URL="http://localhost:4000/v1"
export OPENAI_API_KEY="sk-amase-master-key"
export OPENAI_MODEL_NAME="coding-fleet"
echo "[+] Environment configured to route through LiteLLM Proxy (:4000 -> coding-fleet)."

# 7. Inject executable pre-commit hook that blocks forbidden files
# Resolve the actual git directory from the .git worktree pointer
# If gitdir contains worktre/, the actual repo is two levels up (.. /.. /hooks)
GIT_FILE="$TARGET_REPO/.git"
if [[ -f "$GIT_FILE" ]]; then
  GIT_DIR=$(grep '^gitdir:' "$GIT_FILE" | sed 's/^gitdir: //')
  if [[ "$GIT_DIR" == *"/worktrees/"* ]]; then
    MAIN_HOOK_DIR=$(dirname "$(dirname "$GIT_DIR")")/hooks
  else
    MAIN_HOOK_DIR=$(dirname "$GIT_DIR")/hooks
  fi
else
  MAIN_HOOK_DIR="$TARGET_REPO/.git/hooks"
fi
MAIN_HOOK="$MAIN_HOOK_DIR/pre-commit"
BACKUP_HOOK="$MAIN_HOOK.bak.$TASK_ID"

if [[ -f "$MAIN_HOOK" ]]; then
  cp "$MAIN_HOOK" "$BACKUP_HOOK"
  echo "[+] Backed up existing pre-commit hook."
fi

mkdir -p "$MAIN_HOOK_DIR"

cat > "$MAIN_HOOK" << 'HOOK'
#!/usr/bin/env bash
set -euo pipefail
FORBIDDEN_FILES="package.json .amase/scope.md"
FORBIDDEN_PATTERNS="as any|@ts-ignore"
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)
if [[ -n "$STAGED_FILES" ]]; then
  for f in $FORBIDDEN_FILES; do
    if echo "$STAGED_FILES" | grep -qx "$f"; then
      echo "[-] BLOCKED: Forbidden file '$f' is staged for commit." >&2
      exit 1
    fi
  done
  for pattern in $FORBIDDEN_PATTERNS; do
    if git diff --cached 2>/dev/null | grep -qE "$pattern"; then
      echo "[-] BLOCKED: Forbidden pattern '$pattern' found in staged changes." >&2
      exit 1
    fi
  done
fi
exit 0
HOOK
chmod +x "$MAIN_HOOK"
echo "[+] Injected executable pre-commit hook blocking forbidden files/patterns."

# 8. Make an initial commit on the branch to verify the hook works
echo "[+] Making initial commit on $BRANCH_NAME to verify workflow..."
git -C "$WORKTREE_PATH" checkout "$BRANCH_NAME" >/dev/null 2>&1 || true
echo "test wiring commit" > "$WORKTREE_PATH/test-wiring-init.txt"
git -C "$WORKTREE_PATH" add test-wiring-init.txt >/dev/null 2>&1 || true
git -C "$WORKTREE_PATH" commit -m "chore: initial wiring test commit" >/dev/null 2>&1 || true

# 9. Verify pre-commit hook blocks forbidden files
echo "[+] Verifying pre-commit hook blocks forbidden files..."
mkdir -p "$WORKTREE_PATH/.amase"
echo "forbidden" > "$WORKTREE_PATH/.amase/scope.md"
git -C "$WORKTREE_PATH" add .amase/scope.md >/dev/null 2>&1 || true
STAGED=$(git -C "$WORKTREE_PATH" diff --cached --name-only 2>/dev/null || true)
if echo "$STAGED" | grep -qx ".amase/scope.md"; then
  if git -C "$WORKTREE_PATH" commit -m "test: attempt to add forbidden file" >/dev/null 2>&1; then
    echo "[-] FAIL: Pre-commit hook did not block forbidden file .amase/scope.md"
  else
    echo "[+] PASS: Pre-commit hook correctly blocked forbidden file .amase/scope.md"
  fi
else
  echo "[-] FAIL: .amase/scope.md not staged properly"
fi

# 10. Verify pre-commit hook blocks 'as any' / '@ts-ignore' patterns
echo "[+] Verifying pre-commit hook blocks 'as any' / '@ts-ignore' patterns..."
echo "some code with as any" > "$WORKTREE_PATH/test-ts-ignore.ts"
git -C "$WORKTREE_PATH" add test-ts-ignore.ts >/dev/null 2>&1 || true
STAGED2=$(git -C "$WORKTREE_PATH" diff --cached --name-only 2>/dev/null || true)
if echo "$STAGED2" | grep -q "test-ts-ignore.ts"; then
  if git -C "$WORKTREE_PATH" commit -m "test: attempt to add as any pattern" >/dev/null 2>&1; then
    echo "[-] FAIL: Pre-commit hook did not block 'as any' pattern"
  else
    echo "[+] PASS: Pre-commit hook correctly blocked 'as any' pattern"
  fi
else
  echo "[-] FAIL: test-ts-ignore.ts not staged properly"
fi

# 11. Verify sentinel audit simulation
echo "[+] Verifying sentinel audit simulation..."
SIM_WORKTREE="$WORKTREE_PATH/sim-sentinel"
mkdir -p "$SIM_WORKTREE"
cp -rn "$WORKTREE_PATH/"* "$SIM_WORKTREE/" 2>/dev/null || true
# Create a test file that would trigger a HIGH finding (DOM injection risk)
echo 'element.innerHTML = userInput;' > "$SIM_WORKTREE/test-dom-injection.js"
git -C "$SIM_WORKTREE" add test-dom-injection.js >/dev/null 2>&1 || true
git -C "$SIM_WORKTREE" commit -m "chore: add test DOM injection file" >/dev/null 2>&1 || true
SIM_AUDIT=$(python3 "$ORCHESTRATOR_DIR/scripts/sentinel.py" "$SIM_WORKTREE" 2>&1) || true
if echo "$SIM_AUDIT" | grep -qE '^\[(CRITICAL|HIGH|MEDIUM|LOW|INFO)\]' || echo "$SIM_AUDIT" | grep -q "Core invariants verified clean"; then
  echo "[+] PASS: Sentinel audit produced valid output format"
else
  echo "[-] FAIL: Sentinel audit output format unexpected"
  echo "$SIM_AUDIT"
fi

# 11. Clean up: reset test commits, remove test files
echo "[+] Cleaning up test artifacts..."
git -C "$WORKTREE_PATH" reset --hard HEAD >/dev/null 2>&1 || true
git -C "$WORKTREE_PATH" checkout main >/dev/null 2>&1 || true
rm -f "$WORKTREE_PATH/.amase/scope.md" "$WORKTREE_PATH/test-ts-ignore.ts" "$WORKTREE_PATH/test-wiring-init.txt" 2>/dev/null || true

# 12. Prune the worktree
echo "[+] Pruning worktree and branch..."
git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
git -C "$TARGET_REPO" worktree prune >/dev/null 2>&1 || true

# 13. Restore original pre-commit hook if we backed it up
if [[ -f "$BACKUP_HOOK" ]]; then
  cp "$BACKUP_HOOK" "$MAIN_HOOK"
  rm -f "$BACKUP_HOOK"
  echo "[+] Restored original pre-commit hook."
elif [[ -f "$MAIN_HOOK.bak" ]]; then
  mv "$MAIN_HOOK.bak" "$MAIN_HOOK" 2>/dev/null || true
  echo "[+] Restored pre-commit hook (fallback)."
else
  rm -f "$MAIN_HOOK"
  echo "[+] Removed temporary pre-commit hook."
fi

echo "[+] Test-wiring simulation complete."
exit 0