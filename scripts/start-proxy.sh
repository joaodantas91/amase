#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ORCHESTRATOR_DIR"

# 1. Load environment variables
if [ -f .env ]; then
  set -a
  source .env
  set +a
  echo "[+] Loaded .env file."
else
  echo "[!] Warning: No .env file found. Copy .env.example to .env and add your API keys."
fi

# Auto-detect GitHub token from gh CLI if not already set
if [[ -z "${GITHUB_TOKEN:-}" ]] && command -v gh >/dev/null 2>&1; then
  DETECTED_GH_TOKEN="$(gh auth token 2>/dev/null || true)"
  if [[ -n "$DETECTED_GH_TOKEN" ]]; then
    export GITHUB_TOKEN="$DETECTED_GH_TOKEN"
    echo "[+] Auto-detected GitHub token via gh CLI."
  fi
fi

# 2. Virtual Environment check
if [ ! -d ".venv" ]; then
  echo "[+] Creating Python virtual environment in .venv..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# 3. Ensure LiteLLM is installed
if ! python3 -c "import litellm" 2>/dev/null; then
  echo "[+] Installing litellm[proxy]..."
  pip install --quiet "litellm[proxy]"
fi

# 4. Start LiteLLM Proxy
echo "[+] Starting LiteLLM fallback proxy on http://0.0.0.0:4000..."
exec litellm --config config/litellm-config.yaml --port 4000 --host 0.0.0.0
