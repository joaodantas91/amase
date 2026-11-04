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
