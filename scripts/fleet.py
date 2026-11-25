#!/usr/bin/env python3
"""
AMASE Free Fleet Invocation Helper
Executes prompts against the $0 Free Model Fleet.
Headless, fast, zero GUI tab popups.
1. Checks local LiteLLM Proxy (:4000) if active.
2. Gracefully falls back to headless OpenCode CLI (nemotron-3.5-lightning-free, etc.).
3. Falls back to Local Ollama daemon (localhost:11434) for 100% offline, unlimited tokens.
4. Falls back to GitHub Models (models.github.ai) using GITHUB_TOKEN or gh CLI.
5. Falls back to direct Groq API if key is present.
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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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

# Upstream provider shards: distinct backends to prevent rate-limit (429) collisions during parallel execution
PROVIDER_SHARDS = [
    "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b",  # Shard 1: NVIDIA NIM
    "opencode/beam-free",                            # Shard 2: Beam / OpenCode
    "openrouter/openrouter/free",                    # Shard 3: OpenRouter Free
    "opencode/nemotron-3.5-lightning-free",          # Shard 4: Alternative OpenCode pool
    "opencode/deepseek-v4.1-flash-free",             # Shard 5: DeepSeek flash pool
]


def get_sharded_model(worker_index: int, total_workers: int = 2) -> str:
    """
    Return a distinct upstream provider model for a worker in a concurrent batch,
    ensuring parallel workers do not trigger 429 rate limits against the same API key.
    """
    shards = list(PROVIDER_SHARDS)
    
    # If local Ollama coder is active, prioritize it as a zero-rate-limit shard
    ollama_models = get_local_ollama_models()
    coder_models = [m for m in ollama_models if "coder" in m.lower()]
    if coder_models:
        # Insert local Ollama coder into the shard rotation at index 1
        shards.insert(1, f"ollama/{coder_models[0]}")
    
    return shards[worker_index % len(shards)]



def get_local_ollama_models(host: str = OLLAMA_HOST):
    """Check if local Ollama daemon is reachable and return active model names."""
    try:
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            return models
    except Exception:
        return []


def query_ollama(prompt: str, system_prompt: str = "", model: str = None, host: str = OLLAMA_HOST, timeout: int = 45) -> str:
    """Query local Ollama daemon for offline, zero-cost, unlimited inference."""
    available = get_local_ollama_models(host)
    if not available:
        return ""

    selected_model = model
    if not selected_model or selected_model not in available:
        # Prefer coder models
        coder_models = [m for m in available if "coder" in m.lower()]
        selected_model = coder_models[0] if coder_models else available[0]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024,
        }
    }

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        content_parts = []
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for line in resp:
                if line.strip():
                    chunk = json.loads(line.decode("utf-8"))
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        content_parts.append(text)
                    if chunk.get("done"):
                        LAST_USAGE["tokens_in"] = chunk.get("prompt_eval_count", 0)
                        LAST_USAGE["tokens_out"] = chunk.get("eval_count", 0)
                        LAST_USAGE["model"] = f"ollama/{selected_model}"
            return "".join(content_parts).strip()
    except Exception as e:
        sys.stderr.write(f"[-] Ollama query failed: {e}\n")
        return ""


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
    Local Ollama, GitHub Models, and direct Groq API.
    Runs headlessly in the background with zero tab popups.
    """
    # 0. Pro Tier via Antigravity CLI ('agy') when model_tier == 'pro' or model_hint starts with 'agy/'
    use_pro = os.getenv("AMASE_MODEL_TIER", "").lower() == "pro" or (model_hint and model_hint.startswith("agy/"))
    if not use_pro:
        cfg_path = os.path.join(os.getcwd(), ".amase", "config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path) as cf:
                    if json.load(cf).get("model_tier") == "pro":
                        use_pro = True
            except Exception:
                pass
    if use_pro:
        agy_bin = os.getenv("AGY_BIN", "/home/joao/.local/bin/agy")
        if os.path.exists(agy_bin) and os.access(agy_bin, os.X_OK):
            pro_model = model_hint[4:] if (model_hint and model_hint.startswith("agy/")) else "gemini-3.8-flash-low"
            combined_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            try:
                res = subprocess.run(
                    [agy_bin, "-p", combined_prompt, "--model", pro_model, "--mode", "plan", "--disable-slash-commands"],
                    capture_output=True, text=True, timeout=min(timeout, 45)
                )
                if res.returncode == 0 and res.stdout.strip():
                    LAST_USAGE["model"] = f"agy/{pro_model}"
                    return res.stdout.strip()
            except Exception as e:
                sys.stderr.write(f"[-] Agy Pro query failed: {e}\n")

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

    # 2. Direct Groq fallback if GROQ_API_KEY is present (blazing fast 1-2s response)
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

    # 3. GitHub Models auto-connector fallback (zero-config, 1-2s response)
    gh_content = query_github_models(prompt, system_prompt, model="openai/gpt-4o-mini", timeout=12)
    if gh_content.strip():
        return gh_content.strip()

    # 4. OpenCode CLI fallback (pure headless) with quota cache awareness
    if os.path.exists(OPENCODE_BIN) and os.access(OPENCODE_BIN, os.X_OK):
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

        candidate_models = FREE_MODELS
        if model_hint and model_hint in FREE_MODELS:
            candidate_models = [model_hint] + [m for m in FREE_MODELS if m != model_hint]

        # Check quota manager if available
        try:
            import quota_manager
            candidate_models = [m for m in candidate_models if quota_manager.check_quota(m)[0]]
        except Exception:
            pass

        for m in candidate_models:
            try:
                cmd = [OPENCODE_BIN, "run", "--model", m, combined_prompt]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=min(timeout, 30))
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
                if "Free usage limit reached" in res.stderr or "Free usage limit reached" in res.stdout:
                    try:
                        import quota_manager
                        quota_manager.record_exhaustion(m, reason="Free usage limit reached")
                    except Exception:
                        pass
            except Exception as e:
                sys.stderr.write(f"[-] Fleet model {m} failed: {e}\n")
                continue

    # 5. Local Ollama fallback (strictly opt-in via AMASE_ALLOW_LOCAL_LLM=1 to prevent 100%+ CPU stalls)
    allow_local = os.getenv("AMASE_ALLOW_LOCAL_LLM", "0") in ("1", "true", "True")
    if allow_local:
        ollama_content = query_ollama(prompt, system_prompt, timeout=timeout)
        if ollama_content.strip():
            return ollama_content.strip()

    sys.stderr.write("[-] All free fleet options exhausted.\n")
    return ""


if __name__ == "__main__":
    test_prompt = "Say hello in one word."
    print(query_fleet(test_prompt))
