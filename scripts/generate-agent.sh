#!/usr/bin/env bash
# ==============================================================================
# AMASE Agent Generator & Capability Envelope
# Synthesizes a role-bounded, scope-fenced agent prompt from .amase/scope.md
# ==============================================================================
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  echo "Usage: $0 --repo <repo_path> --role <builder|scout|sentinel> [--task <task_desc>]"
  exit 1
}

REPO_PATH=""
ROLE=""
TASK_DESC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO_PATH="$2"
      shift 2
      ;;
    --role)
      ROLE="$2"
      shift 2
      ;;
    --task)
      TASK_DESC="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -z "$REPO_PATH" || -z "$ROLE" ]]; then
  usage
fi

SCOPE_FILE="$REPO_PATH/.amase/scope.md"
PERSONA_FILE="$ORCHESTRATOR_DIR/personas/$ROLE.md"

if [[ ! -f "$PERSONA_FILE" ]]; then
  echo "[-] Unknown persona role: $ROLE"
  exit 1
fi

SCOPE_CONTENT=""
if [[ -f "$SCOPE_FILE" ]]; then
  SCOPE_CONTENT=$(cat "$SCOPE_FILE")
else
  SCOPE_CONTENT="Standard AMASE Rules: zero dependency creep, zero raw hex colors, zero 'as any'."
fi

PERSONA_CONTENT=$(cat "$PERSONA_FILE")

cat <<EOF
# AMASE Scoped Agent: $ROLE
Timestamp: $(date -Iseconds)
Target Project: $REPO_PATH

## PROJECT SCOPE BOUNDARIES (MANDATORY & ENFORCED):
$SCOPE_CONTENT

## ROLE DIRECTIVES ($ROLE):
$PERSONA_CONTENT

EOF

# Inject AST symbol outline into the agent prompt
AST_SCRIPT="$ORCHESTRATOR_DIR/scripts/outline-ast.py"
if [[ -f "$AST_SCRIPT" ]]; then
  AST_OUTPUT=$(python3 "$AST_SCRIPT" "$REPO_PATH" --include-symbols-only 2>/dev/null) || true
  if [[ -n "$AST_OUTPUT" ]]; then
    echo ""
    echo "## CODEBASE AST SYMBOL MAP"
    printf '%s\n' "$AST_OUTPUT"
  fi
fi

if [[ "$ROLE" == "builder" ]]; then
  cat <<EOF
## BUILDER BOUNDARIES & FORBIDDEN ACTIONS:
- ALLOWED: Edit files in src/ and tests/ relevant to the task.
- FORBIDDEN: NEVER modify package.json or install new npm packages.
- FORBIDDEN: NEVER modify wxt.config.ts manifest permissions without instruction.
- FORBIDDEN: NEVER use raw hex colors in <style> blocks (use tokens.css / components.css).
- FORBIDDEN: NEVER use 'as any' or '@ts-ignore'.
- FORBIDDEN: NEVER touch .amase/scope.md.
- EXIT GATE: All tests in .amase/test-gate.sh must pass with exit code 0 before committing.

ACTIVE TASK TO IMPLEMENT:
$TASK_DESC
EOF
elif [[ "$ROLE" == "scout" ]]; then
  cat <<EOF
## SCOUT BOUNDARIES:
- PERMISSIONS: Strictly Read-Only across the codebase.
- FORBIDDEN: NEVER write, modify, or commit code in src/ or tests/.
- OUTPUT: Write only structured proposals to .amase/discovery.md.
- GATE: Every discovered vertical slice must verify compliance with .amase/scope.md.
EOF
elif [[ "$ROLE" == "sentinel" ]]; then
  cat <<EOF
## SENTINEL BOUNDARIES:
- PERMISSIONS: Strictly Read-Only on git diffs (git diff HEAD~1..HEAD).
- FORBIDDEN: NEVER modify application code.
- OUTPUT: Write vulnerability & invariant audits to AUDIT.md.
EOF
fi
