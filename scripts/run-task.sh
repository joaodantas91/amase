#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  echo "Usage: $0 --repo <path-to-repo> --task <task-id> [--test-cmd <cmd>]"
  echo "Example: $0 --repo /home/joao/dev/kandidat --task fill-button-action --test-cmd 'bunx vitest run'"
  exit 1
}

TARGET_REPO=""
TASK_ID=""
TEST_CMD=""

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
    --test-cmd)
      TEST_CMD="$2"
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
echo " AMASE Autonomous Worktree Task Runner"
echo " Target Repo: $TARGET_REPO"
echo " Task ID:     $TASK_ID"
echo " Branch:      $BRANCH_NAME"
echo " Worktree:    $WORKTREE_PATH"
echo "========================================================"

# 0. Check writable filesystem in TARGET_REPO
if ! touch "$TARGET_REPO/.amase_write_test" 2>/dev/null; then
  echo "[-] ERROR: $TARGET_REPO is read-only in this session."
  echo "[-] Ensure AGY / CLI was started with write permissions on $TARGET_REPO (e.g. 'agy $TARGET_REPO')."
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
  echo "[!] Worktree $WORKTREE_PATH already exists. Pruning..."
  git -C "$TARGET_REPO" worktree remove --force "$WORKTREE_PATH" 2>/dev/null || rm -rf "$WORKTREE_PATH"
fi

# 2b. Auto-commit dirty governance state on main before worktree branching
DIRTY_GOV=$(git -C "$TARGET_REPO" status --porcelain BACKLOG.md .amase 2>/dev/null || true)
if [[ -n "$DIRTY_GOV" ]]; then
  echo "[+] Auto-committing uncommitted governance state on $(git -C "$TARGET_REPO" branch --show-current)..."
  git -C "$TARGET_REPO" add BACKLOG.md .amase/ 2>/dev/null || true
  git -C "$TARGET_REPO" commit -m "chore(amase): sync governance and backlog state" 2>/dev/null || true
fi

# 3. Create isolated ephemeral worktree
echo "[+] Creating Git worktree on branch $BRANCH_NAME..."
git -C "$TARGET_REPO" branch -D "$BRANCH_NAME" 2>/dev/null || true
mkdir -p "$(dirname "$WORKTREE_PATH")"
git -C "$TARGET_REPO" worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH"

# 3b. Safe Environment Inheritance (.env replication with strict .gitignore exclusion)
if [[ -f "$TARGET_REPO/.env" ]]; then
  echo "[+] Parent repository .env detected. Replicating safely to worktree..."
  cp -n "$TARGET_REPO/.env" "$WORKTREE_PATH/.env" 2>/dev/null || true
  if ! grep -qE "^\.env" "$WORKTREE_PATH/.gitignore" 2>/dev/null; then
    echo -e "\n.env\n.env.*\n" >> "$WORKTREE_PATH/.gitignore"
    echo "[+] Ensured .env is excluded in $WORKTREE_PATH/.gitignore"
  fi
fi

# 3c. Replicate gitignored framework build & typegen caches if present in parent repo
FRAMEWORK_CACHES=(".wxt" ".svelte-kit" ".nuxt" ".next/types" ".astro")
for F_CACHE in "${FRAMEWORK_CACHES[@]}"; do
  if [[ -d "$TARGET_REPO/$F_CACHE" && ! -e "$WORKTREE_PATH/$F_CACHE" ]]; then
    echo "[+] Parent framework cache ($F_CACHE) detected. Replicating to worktree..."
    mkdir -p "$(dirname "$WORKTREE_PATH/$F_CACHE")"
    cp -r "$TARGET_REPO/$F_CACHE" "$WORKTREE_PATH/$F_CACHE" 2>/dev/null || true
  fi
done

# Ensure Orca knows this repo and exposes its worktrees
ORCA_SHIM="/home/joao/.config/orca/linux-orca-cli-shim/orca"
if [[ -x "$ORCA_SHIM" ]] && "$ORCA_SHIM" status >/dev/null 2>&1; then
  "$ORCA_SHIM" repo add --path "$TARGET_REPO" >/dev/null 2>&1 || true
  "$ORCA_SHIM" repo set --repo "path:$TARGET_REPO" --external-worktree-visibility show >/dev/null 2>&1 || true
fi

# 4. Inject Scoped Agent Directives & Boundaries into Worktree root
if [[ -x "$ORCHESTRATOR_DIR/scripts/generate-agent.sh" ]]; then
  "$ORCHESTRATOR_DIR/scripts/generate-agent.sh" --repo "$TARGET_REPO" --role builder --task "$TASK_ID" > "$WORKTREE_PATH/.amase-rules.md"
  echo "[+] Generated role-bounded builder directives with scope enforcement in .amase-rules.md"
else
  cat "$ORCHESTRATOR_DIR/prompts/swarm_invariants.md" \
      "$ORCHESTRATOR_DIR/prompts/design.md" \
      "$ORCHESTRATOR_DIR/prompts/ponytail.md" \
      "$ORCHESTRATOR_DIR/prompts/caveman.md" > "$WORKTREE_PATH/.amase-rules.md"
fi

# Link or copy skills so child agents can access them directly
mkdir -p "$WORKTREE_PATH/.agents/skills"
cp -rn "$ORCHESTRATOR_DIR/skills/"* "$WORKTREE_PATH/.agents/skills/" 2>/dev/null || true
echo "[+] Injected skills into worktree."

# 5. Export LiteLLM Gateway Endpoint for worker agents
export OPENAI_BASE_URL="http://localhost:4000/v1"
export OPENAI_API_KEY="sk-amase-master-key"
export OPENAI_MODEL_NAME="coding-fleet"

echo "[+] Environment configured to route through LiteLLM Proxy (:4000 -> coding-fleet)."
echo "[+] Worktree is ready for autonomous execution at: $WORKTREE_PATH"

# 6. Inject executable pre-commit hook into worktree
HOOK_DIR=$(git -C "$WORKTREE_PATH" rev-parse --git-path hooks)
mkdir -p "$HOOK_DIR"
MAIN_HOOK="$HOOK_DIR/pre-commit"

if [[ -f "$MAIN_HOOK" ]]; then
  cp "$MAIN_HOOK" "$MAIN_HOOK.bak"
  echo "[+] Backed up existing pre-commit hook."
fi

# Detect manifest file dynamically for pre-commit protection
MANIFEST_FILE=""
if [[ -f "$WORKTREE_PATH/package.json" ]]; then
  MANIFEST_FILE="package.json"
elif [[ -f "$WORKTREE_PATH/Cargo.toml" ]]; then
  MANIFEST_FILE="Cargo.toml"
elif [[ -f "$WORKTREE_PATH/pyproject.toml" ]]; then
  MANIFEST_FILE="pyproject.toml"
elif [[ -f "$WORKTREE_PATH/requirements.txt" ]]; then
  MANIFEST_FILE="requirements.txt"
elif [[ -f "$WORKTREE_PATH/go.mod" ]]; then
  MANIFEST_FILE="go.mod"
fi

cat > "$MAIN_HOOK" << HOOK
#!/usr/bin/env bash
set -euo pipefail
FORBIDDEN_FILES="${MANIFEST_FILE:+$MANIFEST_FILE }.amase/scope.md"
FORBIDDEN_PATTERNS=("as any" "@ts-ignore")
STAGED_FILES=\$(git diff --cached --name-only 2>/dev/null || true)
if [[ -n "\$STAGED_FILES" ]]; then
  for f in \$FORBIDDEN_FILES; do
    if echo "\$STAGED_FILES" | grep -qx "\$f"; then
      echo "[-] BLOCKED: Forbidden file '\$f' is staged for commit." >&2
      exit 1
    fi
  done
  TS_DIFF=\$(git diff --cached -- '*.ts' '*.tsx' '*.js' '*.jsx' 2>/dev/null || true)
  if [[ -n "\$TS_DIFF" ]]; then
    for pattern in "\${FORBIDDEN_PATTERNS[@]}"; do
      if echo "\$TS_DIFF" | grep -qE "\$pattern"; then
        echo "[-] BLOCKED: Forbidden pattern '\$pattern' found in staged changes." >&2
        exit 1
      fi
    done
  fi
fi
HOOK
exit 0
HOOK

chmod +x "$MAIN_HOOK"
echo "[+] Injected executable pre-commit hook blocking forbidden files/patterns."

# Set chmod 444 on .amase/scope.md in the worktree
chmod 444 "$WORKTREE_PATH/.amase/scope.md" 2>/dev/null || true

# 7. If test gate exists or test command provided, validate baseline
if [[ -z "$TEST_CMD" && -f "$WORKTREE_PATH/.amase/test-gate.sh" ]]; then
  TEST_CMD="$WORKTREE_PATH/.amase/test-gate.sh"
fi

if [[ -n "$TEST_CMD" ]]; then
  echo "[+] Validating baseline tests in worktree using: $TEST_CMD"
  (cd "$WORKTREE_PATH" && eval "$TEST_CMD") || {
    echo "[!] Baseline tests currently failing or unconfigured. Ready for agent to fix/implement."
  }
fi
