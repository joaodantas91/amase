#!/usr/bin/env bash
# ==============================================================================
# AMASE Universal Project Scaffolder
# Auto-detects project type and generates .amase governance files.
# Usage: scripts/init-project.sh [dir]  (defaults to current directory)
# ==============================================================================
set -euo pipefail

TARGET_DIR="${1:-.}"
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

cat > "$TARGET_DIR/.amase/config.json" <<'CONFIG'
{
  "mode": "autonomous",
  "concurrency": "sequential",
  "model_tier": "free",
  "ui": {
    "builder_visible_tab": true,
    "target_url": ""
  },
  "discovery": {
    "enabled": true,
    "max_slices": 2
  }
}
CONFIG

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

cat > "$TARGET_DIR/.amase/discovery.md" <<'DISCOVERY'
# Discovery & Token Optimization Inbox

Staging area for discovered project improvements, features, and token-saving ideas.

---

## Active Proposals

(none yet)
DISCOVERY

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

chmod +x "$TARGET_DIR/.amase/test-gate.sh"

echo "[+] AMASE initialized in $TARGET_DIR"
echo "[+] Detected project type: $PROJECT_TYPE"
echo "[+] Created .amase/config.json, .amase/scope.md, .amase/discovery.md, .amase/test-gate.sh"
