#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

DIFF_ONLY=false
if [[ "${1:-}" == "--diff-only" ]]; then
  DIFF_ONLY=true
fi

if [[ "$DIFF_ONLY" == "true" ]]; then
  echo "[+] Running Fast Targeted Test Gate (--diff-only)..."
  TOUCHED_FILES=$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only HEAD 2>/dev/null || true)
  if [[ -z "$TOUCHED_FILES" ]]; then
    TOUCHED_FILES=$(git status --porcelain 2>/dev/null | awk '{print $2}' || true)
  fi
  for f in $TOUCHED_FILES; do
    if [[ -f "$f" ]]; then
      if [[ "$f" == *.sh || "$f" == "amase" ]]; then
        bash -n "$f"
        echo "  ✓ $f (syntax OK)"
      elif [[ "$f" == *.py ]]; then
        python3 -m py_compile "$f"
        echo "  ✓ $f (compiled OK)"
      elif [[ "$f" == *.js ]]; then
        node -c "$f"
        echo "  ✓ $f (syntax OK)"
      fi
    fi
  done
  echo "[+] Fast Targeted Gate passed."
  exit 0
fi

echo "[+] Running AMASE Self-Test Gate..."

# 1. Validate Bash syntax for all scripts
echo "[+] Validating Bash scripts syntax..."
for script in amase scripts/*.sh; do
  if [[ -f "$script" ]]; then
    bash -n "$script"
    echo "  ✓ $script (syntax OK)"
  fi
done

# 2. Validate Python syntax and compilation
echo "[+] Validating Python scripts compilation..."
python3 -m py_compile scripts/*.py
echo "  ✓ Python scripts compiled cleanly"

if [[ -f "scripts/ui_network_audit.py" ]]; then
  python3 scripts/ui_network_audit.py --mock-test >/dev/null 2>&1
  echo "  ✓ scripts/ui_network_audit.py (mock-test passed)"
fi

if [[ -f "scripts/ui_formatter.py" ]]; then
  python3 scripts/ui_formatter.py >/dev/null 2>&1
  echo "  ✓ scripts/ui_formatter.py (self-test passed)"
fi

if [[ -f "scripts/ui_validator.py" ]]; then
  python3 scripts/ui_validator.py --mock-test >/dev/null 2>&1
  echo "  ✓ scripts/ui_validator.py (mock-test passed)"
fi

if [[ -f "scripts/ui_mcp_server.py" ]]; then
  python3 scripts/ui_mcp_server.py --mock-test >/dev/null 2>&1
  echo "  ✓ scripts/ui_mcp_server.py (mock-test passed)"
fi

if [[ -f "scripts/quota_manager.py" ]]; then
  TMP_Q=$(mktemp /tmp/amase-q-test.XXXXXX.json)
  python3 scripts/quota_manager.py --file "$TMP_Q" --record "opencode/beam-free" --ttl 60 >/dev/null 2>&1
  ! python3 scripts/quota_manager.py --file "$TMP_Q" --check "opencode/beam-free" >/dev/null 2>&1
  python3 scripts/quota_manager.py --file "$TMP_Q" --clear >/dev/null 2>&1
  python3 scripts/quota_manager.py --file "$TMP_Q" --check "opencode/beam-free" >/dev/null 2>&1
  rm -f "$TMP_Q"
  echo "  ✓ scripts/quota_manager.py (self-test passed)"
fi

# 2.1 Validate JavaScript syntax and heuristics self-test
if command -v node >/dev/null 2>&1; then
  echo "[+] Validating JavaScript scripts syntax..."
  for js in scripts/*.js; do
    if [[ -f "$js" ]]; then
      node -c "$js"
      echo "  ✓ $js (syntax OK)"
    fi
  done
  if [[ -f "scripts/ui_heuristics.js" ]]; then
    node scripts/ui_heuristics.js --test >/dev/null 2>&1
    echo "  ✓ scripts/ui_heuristics.js (self-test passed)"
  fi
fi

if command -v shellcheck >/dev/null 2>&1; then
  echo "[+] Running shellcheck on amase and scripts/*.sh..."
  shellcheck amase scripts/*.sh
  echo "  ✓ shellcheck passed"
else
  echo "  ! shellcheck not installed, skipping shellcheck"
fi

if command -v ruff >/dev/null 2>&1; then
  echo "[+] Running ruff check on scripts/*.py..."
  ruff check scripts/*.py
  echo "  ✓ ruff check passed"
elif command -v flake8 >/dev/null 2>&1; then
  echo "[+] Running flake8 check on scripts/*.py..."
  flake8 scripts/*.py
  echo "  ✓ flake8 check passed"
fi

# 3. Verify executable permissions
for script in amase scripts/*.sh scripts/*.py; do
  if [[ -f "$script" && ! -x "$script" ]]; then
    echo "[-] Error: $script is not executable"
    exit 1
  fi
done
echo "  ✓ All scripts are executable"

# 4. Dry-run generate-agent.sh to verify contract
echo "[+] Testing generate-agent.sh dry-run..."
OUTPUT=$(./scripts/generate-agent.sh --repo "$REPO_DIR" --role builder --task "dry-run-test")
if [[ -z "$OUTPUT" ]] || ! echo "$OUTPUT" | grep -q "PROJECT SCOPE BOUNDARIES"; then
  echo "[-] generate-agent.sh dry-run failed validation"
  exit 1
fi
echo "  ✓ generate-agent.sh passed dry-run"

# 5. Optional UI Layout Fast-Gate (for frontend / web targets)
UI_TARGET="${AMASE_UI_URL:-}"
if [[ -z "$UI_TARGET" && -f ".amase/config.json" ]]; then
  UI_TARGET=$(jq -r '.ui.target_url // empty' ".amase/config.json" 2>/dev/null || true)
fi

if [[ -n "$UI_TARGET" ]]; then
  echo "[+] Running AMASE UI Fast-Gate on $UI_TARGET..."
  if command -v amase >/dev/null 2>&1; then
    amase ui-check "$UI_TARGET"
  elif [[ -f "scripts/ui_validator.py" ]]; then
    python3 scripts/ui_validator.py "$UI_TARGET"
  fi
  echo "  ✓ UI layout check passed"
fi

echo "[+] AMASE Orchestrator Test Gate passed with exit code 0."
