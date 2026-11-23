#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

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

echo "[+] AMASE Orchestrator Test Gate passed with exit code 0."
