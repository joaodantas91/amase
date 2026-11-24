#!/usr/bin/env python3
"""
AMASE Free Fleet Invocation Helper
Executes prompts against the $0 Free Model Fleet.
Headless, fast, zero GUI tab popups.
1. Checks local LiteLLM Proxy (:4000) if active.
2. Gracefully falls back to headless OpenCode CLI (nemotron-3.5-lightning-free, etc.).
"""
import os
import sys
import json
import subprocess
import urllib.request

OPENCODE_BIN = os.getenv("OPENCODE_BIN", "/home/joao/.bun/bin/opencode")
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")

FREE_MODELS = [
    "opencode/nemotron-3.5-lightning-free",
    "opencode/beam-free",
    "opencode/deepseek-v4.1-flash-free",
    "opencode/flint-40b-free",
    "opencode/mimo-v2.6-flash-free",
]

def query_fleet(prompt: str, system_prompt: str = "", model_hint: str = None, title: str = "", timeout: int = 60) -> str:
    """
    Query the free model pool with automatic failover between LiteLLM and OpenCode CLI.
    Runs headlessly in the background with zero tab popups.
    """
    # 1. Try LiteLLM proxy if reachable
    try:
        model = model_hint or "scout-fleet"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are an autonomous AMASE agent."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        req = urllib.request.Request(
            LITELLM_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            if content.strip():
                return content.strip()
    except Exception:
        pass  # Fall back to OpenCode CLI

    # 2. OpenCode CLI fallback (pure headless)
    if os.path.exists(OPENCODE_BIN) and os.access(OPENCODE_BIN, os.X_OK):
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

        candidate_models = FREE_MODELS
        if model_hint and model_hint in FREE_MODELS:
            candidate_models = [model_hint] + [m for m in FREE_MODELS if m != model_hint]

        for m in candidate_models:
            try:
                cmd = [OPENCODE_BIN, "run", "--model", m, combined_prompt]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception as e:
                sys.stderr.write(f"[-] Fleet model {m} failed: {e}\n")
                continue

    sys.stderr.write("[-] All free fleet options exhausted.\n")
    return ""

if __name__ == "__main__":
    test_prompt = "Say hello in one word."
    print(query_fleet(test_prompt))
