#!/usr/bin/env python3
"""
AMASE Environment & Prerequisite Health Check (amase doctor)
Verifies all runtime dependencies, model proxies, git capabilities,
and project governance configurations.
"""
import os
import sys
import shutil
import subprocess
import urllib.request
import json

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_git(target_dir):
    git_bin = shutil.which("git")
    if not git_bin:
        return "FAIL", "Git is not installed or not in PATH."
    try:
        ver = subprocess.run([git_bin, "--version"], capture_output=True, text=True, check=True).stdout.strip()
        # Verify inside repository
        res = subprocess.run([git_bin, "-C", target_dir, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
        if res.returncode == 0:
            return "PASS", f"{ver} (Valid repository at {target_dir})"
        else:
            return "WARN", f"{ver} (Not inside a git repository: run 'git init')"
    except Exception as e:
        return "FAIL", f"Git check failed: {e}"


def check_python():
    v = sys.version_info
    ver_str = f"Python {v.major}.{v.minor}.{v.micro}"
    if v.major >= 3 and v.minor >= 10:
        return "PASS", ver_str
    return "WARN", f"{ver_str} (Recommended: Python 3.10+)"


def check_opencode():
    op_path = os.getenv("OPENCODE_BIN", "/home/joao/.bun/bin/opencode")
    if not os.path.exists(op_path):
        op_path = shutil.which("opencode")
    if op_path and os.path.exists(op_path) and os.access(op_path, os.X_OK):
        return "PASS", f"OpenCode CLI located at {op_path}"
    return "WARN", "OpenCode CLI not found in ~/.bun/bin or PATH. Free fleet builder will use fallback."


def check_opencode_db():
    db_path = os.path.expanduser("~/.local/share/opencode/opencode.db")
    if not os.path.exists(db_path):
        return "WARN", f"OpenCode DB not found at {db_path} (initialized on first run)"
    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=3.0)
        cursor = conn.cursor()
        mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        if mode.lower() != "wal":
            cursor.execute("PRAGMA journal_mode = WAL;")
            mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        cursor.execute("PRAGMA busy_timeout = 5000;")
        conn.close()
        return "PASS", f"OpenCode SQLite WAL mode active ({mode.upper()}) at {db_path}"
    except Exception as e:
        return "WARN", f"OpenCode DB check failed: {e}"



def check_litellm():
    url = os.getenv("LITELLM_URL", "http://localhost:4000/health")
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer sk-amase-master-key"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                return "PASS", "LiteLLM fallback proxy active on http://localhost:4000"
    except Exception:
        pass
    return "WARN", "LiteLLM proxy offline on :4000. Start it via 'scripts/start-proxy.sh' if fallback is needed."


def check_terminal_tab():
    ptyxis = shutil.which("ptyxis") or "/usr/bin/ptyxis"
    has_display = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
    if os.path.exists(ptyxis) and has_display:
        return "PASS", f"Ptyxis terminal tab multiplexer ready ({ptyxis})"
    elif not has_display:
        return "PASS", "Headless environment detected (workers will run in headless background mode)"
    return "WARN", "Ptyxis terminal not found. Workers will run in clean headless background mode."


def check_api_keys(orchestrator_dir):
    env_file = os.path.join(orchestrator_dir, ".env")
    keys_found = []
    keys_to_check = ["NVIDIA_API_KEY", "GROQ_API_KEY", "OPEN_ROUTER_API_KEY"]
    
    # Read from environment or .env
    for k in keys_to_check:
        if os.getenv(k):
            keys_found.append(k)

    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                for k in keys_to_check:
                    if line.startswith(f"{k}=") and k not in keys_found:
                        val = line.split("=", 1)[1].strip()
                        if val and not val.startswith("your_"):
                            keys_found.append(k)

    if len(keys_found) >= 2:
        return "PASS", f"Active API keys: {', '.join(keys_found)}"
    elif len(keys_found) >= 1:
        return "PASS", f"Active API key: {', '.join(keys_found)}"
    return "WARN", "No API keys found in environment or .env. Add keys to enable NVIDIA / Groq free fleet."


def check_github_models():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    source = "environment"
    if not token:
        try:
            token = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL, text=True).strip()
            source = "gh CLI"
        except Exception:
            token = ""

    if token:
        return "PASS", f"GitHub token detected ({source}). GitHub Models auto-connector ready."
    return "WARN", "No GitHub token found. (Run 'gh auth login' or export GITHUB_TOKEN to enable free GitHub Models)."


def check_ollama():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            if models:
                return "PASS", f"Local Ollama online (Active models: {', '.join(models)})"
            return "WARN", "Local Ollama daemon online, but no models downloaded yet. (Run 'ollama pull qwen2.5-coder:14b')"
    except Exception:
        pass
    return "WARN", "Local Ollama offline. (Run 'ollama serve' or start service for offline fallback)"


def check_governance(target_dir):
    config_file = os.path.join(target_dir, ".amase", "config.json")
    scope_file = os.path.join(target_dir, ".amase", "scope.md")
    test_gate = os.path.join(target_dir, ".amase", "test-gate.sh")

    present = []
    if os.path.exists(config_file):
        present.append("config.json")
    if os.path.exists(scope_file):
        present.append("scope.md")
    if os.path.exists(test_gate):
        present.append("test-gate.sh")

    if len(present) == 3:
        return "PASS", f"Project governance initialized ({', '.join(present)})"
    elif len(present) > 0:
        return "WARN", f"Partial governance initialized: missing {[f for f in ('config.json', 'scope.md', 'test-gate.sh') if f not in present]}"
    return "WARN", "Project not initialized for AMASE: run 'amase init' to scaffold governance."


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    target_dir = os.path.abspath(target_dir)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    orchestrator_dir = os.path.dirname(scripts_dir)

    print(f"\n{BOLD}========================================================")
    print(" AMASE System & Project Health Check (amase doctor)")
    print(f" Target Directory: {target_dir}")
    print(f"========================================================{RESET}\n")

    checks = [
        ("Git Version & Worktrees", check_git(target_dir)),
        ("Python Runtime", check_python()),
        ("OpenCode CLI Tool", check_opencode()),
        ("OpenCode SQLite Safety", check_opencode_db()),
        ("LiteLLM Proxy (:4000)", check_litellm()),
        ("Terminal Multiplexer", check_terminal_tab()),
        ("Model Fleet API Keys", check_api_keys(orchestrator_dir)),
        ("GitHub Models Connector", check_github_models()),
        ("Local Ollama Engine", check_ollama()),
        ("Project Governance", check_governance(target_dir)),
    ]

    passes = 0
    warns = 0
    fails = 0

    for name, (status, detail) in checks:
        if status == "PASS":
            badge = f"{GREEN}[PASS]{RESET}"
            passes += 1
        elif status == "WARN":
            badge = f"{YELLOW}[WARN]{RESET}"
            warns += 1
        else:
            badge = f"{RED}[FAIL]{RESET}"
            fails += 1

        print(f"  {badge} {BOLD}{name:<25}{RESET} {detail}")

    print(f"\n{BOLD}--------------------------------------------------------")
    print(f" Summary: {GREEN}{passes} passed{RESET}, {YELLOW}{warns} warnings{RESET}, {RED}{fails} failures{RESET}")
    print(f"--------------------------------------------------------{RESET}\n")

    if fails > 0:
        print(f"{RED}[!] Action required: Resolve critical failures before running autonomous loop.{RESET}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}[✓] System is in good position to orchestrate project tasks.{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
