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
  SCOPE_CONTENT=$(cat "$SCOPE_FILE" | python3 "$ORCHESTRATOR_DIR/scripts/prune-prompt.py")
else
  SCOPE_CONTENT="Standard AMASE Rules: zero dependency creep, zero raw hex colors, zero 'as any'."
fi

PERSONA_CONTENT=$(cat "$PERSONA_FILE" | python3 "$ORCHESTRATOR_DIR/scripts/prune-prompt.py")

cat <<EOF
# AMASE Scoped Agent: $ROLE
Timestamp: $(date -Iseconds)
Target Project: $REPO_PATH

## PROJECT SCOPE BOUNDARIES (MANDATORY & ENFORCED):
$SCOPE_CONTENT

## ROLE DIRECTIVES ($ROLE):
$PERSONA_CONTENT

EOF

# Check centralized retrospective flight recorder for adaptive learned guardrails
GLOBAL_RETRO="$HOME/.amase/retrospectives.jsonl"
LOCAL_RETRO="$REPO_PATH/.amase/retrospectives.jsonl"
ADAPTIVE_GUARDRAILS=()

has_retro_sig() {
  local sig="$1"
  if [[ -f "$GLOBAL_RETRO" ]] && grep -q "\"failure_signature\": \"$sig\"" "$GLOBAL_RETRO" 2>/dev/null; then
    return 0
  fi
  if [[ -f "$LOCAL_RETRO" ]] && grep -q "\"failure_signature\": \"$sig\"" "$LOCAL_RETRO" 2>/dev/null; then
    return 0
  fi
  return 1
}

if has_retro_sig "CONTEXT_BLOAT"; then
  ADAPTIVE_GUARDRAILS+=("- [ADAPTIVE GUARDRAIL: CONTEXT_BLOAT PREVIOUSLY DETECTED] Do NOT scan directories or read files outside the files explicitly listed in the active task.")
fi
if has_retro_sig "COMPILER_ERROR"; then
  ADAPTIVE_GUARDRAILS+=("- [ADAPTIVE GUARDRAIL: COMPILER_ERROR PREVIOUSLY DETECTED] Always verify types and run local test suite before committing.")
fi
if has_retro_sig "SOCKET_STALL"; then
  ADAPTIVE_GUARDRAILS+=("- [ADAPTIVE GUARDRAIL: SOCKET_STALL PREVIOUSLY DETECTED] Do not run interactive or long-running commands that block standard input.")
fi

# Inject AST symbol outline into the agent prompt
AST_SCRIPT="$ORCHESTRATOR_DIR/scripts/outline-ast.py"
if [[ -f "$AST_SCRIPT" ]]; then
  FILTER_ARGS=()
  if [[ -n "$TASK_DESC" ]]; then
    for word in stats telemetry sentinel scout settle abort dispatch; do
      if echo "$TASK_DESC" | grep -qi "$word"; then
        FILTER_ARGS=("--filter" "$word")
        break
      fi
    done
  fi

  if has_retro_sig "CONTEXT_BLOAT"; then
    AST_OUTPUT=$(python3 "$AST_SCRIPT" "$REPO_PATH" --include-symbols-only "${FILTER_ARGS[@]}" 2>/dev/null | head -n 50) || true
  else
    AST_OUTPUT=$(python3 "$AST_SCRIPT" "$REPO_PATH" --include-symbols-only "${FILTER_ARGS[@]}" 2>/dev/null) || true
  fi
  if [[ -n "$AST_OUTPUT" ]]; then
    echo ""
    echo "## CODEBASE AST SYMBOL MAP"
    printf '%s\n' "$AST_OUTPUT"
  fi
fi

if [[ "${#ADAPTIVE_GUARDRAILS[@]}" -gt 0 ]]; then
  echo ""
  echo "## ADAPTIVE EXPERIENCE GUARDRAILS (LEARNED FROM RECENT FAILURES):"
  for g in "${ADAPTIVE_GUARDRAILS[@]}"; do
    echo "$g"
  done
fi

MANIFEST_FILE=""
if [[ -f "$REPO_PATH/package.json" ]]; then
  MANIFEST_FILE="package.json"
elif [[ -f "$REPO_PATH/Cargo.toml" ]]; then
  MANIFEST_FILE="Cargo.toml"
elif [[ -f "$REPO_PATH/pyproject.toml" ]]; then
  MANIFEST_FILE="pyproject.toml"
elif [[ -f "$REPO_PATH/requirements.txt" ]]; then
  MANIFEST_FILE="requirements.txt"
elif [[ -f "$REPO_PATH/go.mod" ]]; then
  MANIFEST_FILE="go.mod"
fi

if [[ "$ROLE" == "builder" ]]; then
  cat <<EOF
## BUILDER BOUNDARIES & FORBIDDEN ACTIONS:
- ALLOWED: Edit source and test files relevant to the active task.
- FORBIDDEN: NEVER modify dependency manifests (${MANIFEST_FILE:-project dependencies}) or add unapproved external packages without instruction.
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
