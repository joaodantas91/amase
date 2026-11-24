#!/usr/bin/env python3
"""
AMASE Free Fleet Invocation Helper
Executes prompts against the $0 Free Model Fleet.
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

PTYXIS_BIN = os.getenv("PTYXIS_BIN", "/usr/bin/ptyxis")
HAS_DISPLAY = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))

FREE_MODELS = [
    "opencode/nemotron-3.5-lightning-free",
    "opencode/beam-free",
    "opencode/deepseek-v4.1-flash-free",
    "opencode/flint-40b-free",
    "opencode/mimo-v2.6-flash-free",
]

def _run_in_tab(cmd_prompt: str, model: str, title: str, timeout: int) -> str:
    """Run model inside a dedicated visible Ptyxis terminal tab."""
    import tempfile
    import time
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as prompt_f:
        prompt_f.write(cmd_prompt)
        prompt_file = prompt_f.name

    out_file = prompt_file + ".out"
    done_file = prompt_file + ".done"
    runner_file = prompt_file + ".sh"

    script_content = f"""#!/usr/bin/env bash
set -uo pipefail
echo "=========================================================="
echo "[+] AMASE Agent: {title}"
echo "[+] Model:       {model}"
echo "=========================================================="
PROMPT=$(cat "{prompt_file}")
"{OPENCODE_BIN}" run --model "{model}" "$PROMPT" 2>&1 | tee "{out_file}"
touch "{done_file}"
echo ""
echo "[+] Task complete. Auto-closing tab in 2s..."
sleep 2
exit 0
"""
    with open(runner_file, "w") as rf:
        rf.write(script_content)
    os.chmod(runner_file, 0o755)

    try:
        subprocess.Popen([PTYXIS_BIN, "--tab", f"--title={title}", "--", runner_file])
        start = time.time()
        while time.time() - start < timeout:
            if os.path.exists(done_file):
                time.sleep(0.5)
                if os.path.exists(out_file):
                    with open(out_file, "r") as of:
                        content = of.read().strip()
                        if content:
                            return content
                break
            time.sleep(1)
    finally:
        for f in (prompt_file, out_file, done_file, runner_file):
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except Exception:
                pass
    return ""

def query_fleet(prompt: str, system_prompt: str = "", model_hint: str = None, title: str = "AMASE: Agent", timeout: int = 120) -> str:
    """
    Query the free model pool with automatic failover between LiteLLM and OpenCode CLI.
    When a display is available, opens a visible tab in Ptyxis for user visibility.
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

    # 2. OpenCode CLI fallback
    if os.path.exists(OPENCODE_BIN) and os.access(OPENCODE_BIN, os.X_OK):
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

        candidate_models = FREE_MODELS
        if model_hint and model_hint in FREE_MODELS:
            candidate_models = [model_hint] + [m for m in FREE_MODELS if m != model_hint]

        for m in candidate_models:
            try:
                # If display is active, open in dedicated visible tab
                if HAS_DISPLAY and os.path.exists(PTYXIS_BIN) and os.access(PTYXIS_BIN, os.X_OK):
                    res_content = _run_in_tab(combined_prompt, m, title, timeout)
                    if res_content:
                        return res_content
                else:
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
    test_prompt = "Propose 1 vertical slice task for a web extension."
    print("Testing query_fleet...")
    print(query_fleet(test_prompt))
