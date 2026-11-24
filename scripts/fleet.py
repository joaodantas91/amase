#!/usr/bin/env python3
"""
AMASE Free Fleet Invocation Helper
Executes prompts against the $0 Free Model Fleet.
Headless, fast, zero GUI tab popups.
1. Checks local LiteLLM Proxy (:4000) if active.
2. Gracefully falls back to headless OpenCode CLI (nemotron-3.5-lightning-free, etc.).
3. Falls back to GitHub Models (models.github.ai) using GITHUB_TOKEN or gh CLI.
4. Falls back to direct Groq API if key is present.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OPENCODE_BIN = os.getenv("OPENCODE_BIN", "/home/joao/.bun/bin/opencode")
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000/v1/chat/completions")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-amase-master-key")

LAST_USAGE = {"tokens_in": 0, "tokens_out": 0, "model": ""}


def get_last_usage():
    """Return token usage dictionary from the most recent fleet call."""
    return dict(LAST_USAGE)


FREE_MODELS = [
    "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b",
    "openrouter/openrouter/free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/beam-free",
    "opencode/deepseek-v4.1-flash-free",
    "opencode/flint-40b-free",
    "opencode/mimo-v2.6-flash-free",
]


def get_github_token() -> str:
    """Resolve GitHub token from environment, .env, or gh CLI."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token and not token.startswith("your_"):
        return token

    # Check orchestrator .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GITHUB_TOKEN=") or line.startswith("GH_TOKEN="):
                        t = line.strip().split("=", 1)[1].strip('"\'')
                        if t and not t.startswith("your_"):
                            return t
        except Exception:
            pass

    # Check gh auth token
    try:
        gh_out = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL, text=True).strip()
        if gh_out and gh_out.startswith("gh"):
            return gh_out
    except Exception:
        pass

    return ""


def query_github_models(prompt: str, system_prompt: str = "", model: str = "openai/gpt-4o-mini", timeout: int = 15) -> str:
    """Direct query to GitHub Models inference service (models.github.ai)."""
    token = get_github_token()
    if not token:
        return ""

    url = "https://models.github.ai/inference/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AMASE/1.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            usage = data.get("usage", {})
            LAST_USAGE["tokens_in"] = usage.get("prompt_tokens", 0)
            LAST_USAGE["tokens_out"] = usage.get("completion_tokens", 0)
            LAST_USAGE["model"] = f"github/{model}"
            content = data["choices"][0]["message"].get("content") or ""
            return content.strip()
    except Exception as e:
        sys.stderr.write(f"[-] GitHub Models query failed: {e}\n")
        return ""


def query_fleet(prompt: str, system_prompt: str = "", model_hint: str = None, title: str = "", timeout: int = 60) -> str:
    """
    Query the free model pool with automatic failover across LiteLLM, OpenCode CLI,
    GitHub Models, and direct Groq API.
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
            usage = data.get("usage", {})
            LAST_USAGE["tokens_in"] = usage.get("prompt_tokens", 0)
            LAST_USAGE["tokens_out"] = usage.get("completion_tokens", 0)
            LAST_USAGE["model"] = model
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            if content.strip():
                return content.strip()
    except Exception:
        pass  # Fall back to next options

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

    # 3. GitHub Models auto-connector fallback (zero-config if gh token present)
    gh_content = query_github_models(prompt, system_prompt, model="openai/gpt-4o-mini", timeout=12)
    if gh_content.strip():
        return gh_content.strip()

    # 4. Direct Groq fallback if GROQ_API_KEY is present
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        groq_key = line.strip().split("=", 1)[1].strip('"\'')
                        break
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": "openai/gpt-oss-120b",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1024,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "curl/8.0.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                usage = data.get("usage", {})
                LAST_USAGE["tokens_in"] = usage.get("prompt_tokens", 0)
                LAST_USAGE["tokens_out"] = usage.get("completion_tokens", 0)
                LAST_USAGE["model"] = "openai/gpt-oss-120b"
                content = data["choices"][0]["message"]["content"]
                if content.strip():
                    return content.strip()
        except Exception as e:
            sys.stderr.write(f"[-] Direct Groq fallback failed: {e}\n")

    sys.stderr.write("[-] All free fleet options exhausted.\n")
    return ""


if __name__ == "__main__":
    test_prompt = "Say hello in one word."
    print(query_fleet(test_prompt))
