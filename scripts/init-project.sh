#!/usr/bin/env bash
# ==============================================================================
# AMASE Universal Project Scaffolder & Auto-Healer
# Auto-detects project type, initializes or heals .amase governance files.
# Usage:
#   scripts/init-project.sh [dir] [--heal]
# ==============================================================================
set -euo pipefail

IS_HEAL=0
TARGET_DIR="."

for arg in "$@"; do
  if [[ "$arg" == "--heal" ]]; then
    IS_HEAL=1
  elif [[ "$arg" != -* ]]; then
    TARGET_DIR="$arg"
  fi
done

if [[ ! -d "$TARGET_DIR" ]]; then
  mkdir -p "$TARGET_DIR"
fi
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

PROJECT_TYPE="unknown"
if [[ -f "$TARGET_DIR/package.json" ]]; then
  PROJECT_TYPE="node"
elif [[ -f "$TARGET_DIR/pyproject.toml" || -f "$TARGET_DIR/requirements.txt" ]]; then
  PROJECT_TYPE="python"
elif [[ -f "$TARGET_DIR/Cargo.toml" ]]; then
  PROJECT_TYPE="rust"
elif [[ -f "$TARGET_DIR/go.mod" ]]; then
  PROJECT_TYPE="go"
fi

mkdir -p "$TARGET_DIR/.amase"

# 1. Config Auto-Heal / Generate (Schema Version 2)
CONFIG_FILE="$TARGET_DIR/.amase/config.json"
python3 -c "
import json, os

cfg_path = '$CONFIG_FILE'
defaults = {
    'schema_version': 2,
    'mode': 'autonomous',
    'concurrency': 'sequential',
    'model_tier': 'free',
    'ui': {
        'builder_visible_tab': True,
        'target_url': ''
    },
    'discovery': {
        'enabled': True,
        'max_slices': 2
    }
}

data = {}
if os.path.exists(cfg_path):
    try:
        with open(cfg_path, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}

data['schema_version'] = 2
for k, v in defaults.items():
    if k not in data:
        data[k] = v
    elif isinstance(v, dict) and isinstance(data[k], dict):
        for sub_k, sub_v in v.items():
            if sub_k not in data[k]:
                data[k][sub_k] = sub_v

with open(cfg_path, 'w') as f:
    json.dump(data, f, indent=2)
"

# 2. Scope file (never overwrite existing)
if [[ ! -f "$TARGET_DIR/.amase/scope.md" ]]; then
  cat > "$TARGET_DIR/.amase/scope.md" <<'SCOPE'
# AMASE Project Scope & Governance Boundaries

Core Invariant: **MAXIMUM TOKEN DIET ($0 WORKER FLEET)**.

## 1. Allowed Scope (Green Zone)
- Application source and tests relevant to the task.
- Automation scripts in `scripts/`.
- Prompt specifications in `personas/` and `prompts/`.
- Test gate and validation in `.amase/test-gate.sh`.

## 2. Strictly Forbidden (Red Zone)
- **NO Paid Model Usage for Workers:** Workers must ALWAYS use the $0 Free Fleet.
- **NO Hardcoded Secrets:** Never commit real API keys or tokens. Use environment variables.
- **NO Context Bloat:** Keep prompts dense and terse. Never dump full git histories into prompts.
- **NO Heavy Runtimes:** Prefer standard libraries. No unnecessary dependencies.
- **NO Type Bypasses:** Never use type assertions or ignore directives.
- **NO Scope Edits:** Never modify `.amase/scope.md`.
SCOPE
fi

# 3. Discovery file (never overwrite existing)
if [[ ! -f "$TARGET_DIR/.amase/discovery.md" ]]; then
  cat > "$TARGET_DIR/.amase/discovery.md" <<'DISCOVERY'
# Discovery & Token Optimization Inbox

Staging area for discovered project improvements, features, and token-saving ideas.

---

## Active Proposals

(none yet)
DISCOVERY
fi

# 4. Test gate file (generate only if missing)
if [[ ! -f "$TARGET_DIR/.amase/test-gate.sh" ]]; then
  case "$PROJECT_TYPE" in
    node)
      cat > "$TARGET_DIR/.amase/test-gate.sh" <<'GATE'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[+] Running AMASE Test Gate (Node)..."

if command -v bun >/dev/null 2>&1; then
  if grep -q '"test"[[:space:]]*:' package.json 2>/dev/null; then
    bun run test
  else
    bun test
  fi
else
  npm test
fi

# Optional UI Fast-Gate
UI_TARGET="${AMASE_UI_URL:-}"
if [[ -z "$UI_TARGET" && -f ".amase/config.json" ]]; then
  UI_TARGET=$(jq -r '.ui.target_url // empty' ".amase/config.json" 2>/dev/null || true)
fi
if [[ -n "$UI_TARGET" ]] && command -v amase >/dev/null 2>&1; then
  echo "[+] Running AMASE UI Fast-Gate on $UI_TARGET..."
  amase ui-check "$UI_TARGET"
fi
GATE
      ;;
    python)
      cat > "$TARGET_DIR/.amase/test-gate.sh" <<'GATE'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[+] Running AMASE Test Gate (Python)..."

if command -v pytest >/dev/null 2>&1; then
  pytest
else
  python3 -m pytest
fi
GATE
      ;;
    rust)
      cat > "$TARGET_DIR/.amase/test-gate.sh" <<'GATE'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[+] Running AMASE Test Gate (Rust)..."
cargo test
GATE
      ;;
    go)
      cat > "$TARGET_DIR/.amase/test-gate.sh" <<'GATE'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[+] Running AMASE Test Gate (Go)..."
go test ./...
GATE
      ;;
    *)
      cat > "$TARGET_DIR/.amase/test-gate.sh" <<'GATE'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "[+] Running AMASE Test Gate (unknown project type)..."
echo "[!] No recognized project type detected; nothing to run."
GATE
      ;;
  esac
fi

chmod +x "$TARGET_DIR/.amase/test-gate.sh"

# 5. Universal AGENTS.md in project root (standard for all AI tools: Claude Code, OpenCode, Cursor, Antigravity)
AGENTS_FILE="$TARGET_DIR/AGENTS.md"
if [[ ! -f "$AGENTS_FILE" ]]; then
  cat > "$AGENTS_FILE" <<'AGENTS'
# Project AI Protocol

When an AI assistant or coordinator is opened in this repository:

1. **NEVER modify or write code directly in the assistant/coordinator session.**
   All implementation, refactoring, testing, and debugging are executed exclusively by child worker personas via the $0 Free Fleet in isolated git worktrees.

2. **One-Command Autonomous Execution:**
   - **Inspect Status:** Run `amase status` for an instant unified status overview.
   - **Execute Tasks:** Run `amase` in the terminal.
   - **DO NOT** read internal orchestrator scripts (`run-task.sh`, `settle-task.sh`, `amase` source) or manually commit files. AMASE handles governance auto-healing, git auto-syncing, worker dispatching ($0 models), deterministic test gates, and git settlement autonomously.

3. **Invariants:**
   - **CAVEMAN**: Terse, factual updates. Zero conversational filler or pleasantries.
   - **PONYTAIL**: Minimal working diffs, YAGNI, standard library first.
   - **CHISLE**: Strict context hygiene.
AGENTS
elif ! grep -q "amase status" "$AGENTS_FILE" 2>/dev/null; then
  TMP_AGENTS=$(mktemp)
  cat > "$TMP_AGENTS" <<'AGENTS'
# AMASE Coordinator Protocol
When an AI assistant or coordinator is opened in this repository:
- Run `amase status` to inspect project and backlog state.
- Run `amase` in the terminal to execute backlog tasks autonomously.
- NEVER modify or write code directly in the assistant session; child workers execute tasks in isolated worktrees via the $0 Free Fleet.

AGENTS
  cat "$AGENTS_FILE" >> "$TMP_AGENTS"
  mv "$TMP_AGENTS" "$AGENTS_FILE"
fi

if [[ "$IS_HEAL" -eq 1 ]]; then
  echo "[+] AMASE governance healed in $TARGET_DIR (schema v2)"
else
  echo "[+] AMASE initialized in $TARGET_DIR (schema v2)"
  echo "[+] Detected project type: $PROJECT_TYPE"
  echo "[+] Governance ready: AGENTS.md, .amase/config.json, .amase/scope.md, .amase/discovery.md, .amase/test-gate.sh"
fi
