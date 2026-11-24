#!/usr/bin/env python3
"""
AMASE Project & Fleet Status Inspector (amase status)
Provides an instant, unified 1-read overview of project governance,
backlog queue, git working tree state, and model fleet readiness.
"""
import os
import sys
import json
import re
import shutil
import subprocess
import urllib.request

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def detect_project_type(target_dir):
    if os.path.exists(os.path.join(target_dir, "package.json")):
        return "node"
    if os.path.exists(os.path.join(target_dir, "Cargo.toml")):
        return "rust"
    if os.path.exists(os.path.join(target_dir, "pyproject.toml")) or os.path.exists(os.path.join(target_dir, "requirements.txt")):
        return "python"
    if os.path.exists(os.path.join(target_dir, "go.mod")):
        return "go"
    return "generic"


def get_backlog_stats(target_dir):
    backlog_path = os.path.join(target_dir, "BACKLOG.md")
    if not os.path.exists(backlog_path):
        return None, 0, 0

    pending = []
    completed_count = 0
    next_task = None

    try:
        with open(backlog_path, "r", errors="ignore") as f:
            for line in f:
                if re.match(r'^- \[x\]', line.strip(), re.IGNORECASE):
                    completed_count += 1
                elif re.match(r'^- \[ \]', line.strip()):
                    clean = line.strip().replace("- [ ]", "").strip()
                    clean = re.sub(r'^\*\*([^*]+)\*\*:?', r'\1:', clean)
                    pending.append(clean)
                    if not next_task:
                        next_task = clean
    except Exception:
        pass

    total = completed_count + len(pending)
    return next_task, len(pending), total


def get_git_state(target_dir):
    if not shutil.which("git"):
        return "Git not installed"
    try:
        res = subprocess.run(["git", "-C", target_dir, "status", "--porcelain"], capture_output=True, text=True)
        if res.returncode != 0:
            return "Not a git repository"
        lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
        if not lines:
            return "Clean"
        gov_dirty = [l for l in lines if "BACKLOG.md" in l or ".amase" in l]
        other_dirty = [l for l in lines if l not in gov_dirty]
        if gov_dirty and not other_dirty:
            return f"Dirty ({len(gov_dirty)} governance files: auto-committed on run)"
        elif gov_dirty and other_dirty:
            return f"Dirty ({len(gov_dirty)} governance, {len(other_dirty)} source files)"
        return f"Dirty ({len(other_dirty)} uncommitted source files)"
    except Exception as e:
        return f"Error: {e}"


def get_active_worktrees(target_dir):
    if not shutil.which("git"):
        return []
    try:
        res = subprocess.run(["git", "-C", target_dir, "worktree", "list"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            return [l for l in lines if ".worktrees" in l]
    except Exception:
        pass
    return []


def get_retrospectives_count(target_dir):
    retro_path = os.path.expanduser("~/.amase/retrospectives.jsonl")
    if not os.path.exists(retro_path):
        return 0, 0, 0, 0
    total = 0
    proj_count = 0
    proj_success = 0
    target_abs = os.path.abspath(target_dir)
    try:
        with open(retro_path, "r", errors="ignore") as f:
            for line in f:
                if line.strip():
                    total += 1
                    try:
                        d = json.loads(line)
                        if d.get("project") == target_abs or d.get("project_name") == os.path.basename(target_abs):
                            proj_count += 1
                            if d.get("failure_signature") == "SUCCESS":
                                proj_success += 1
                    except Exception:
                        pass
    except Exception:
        pass
    proj_failures = proj_count - proj_success
    return proj_success, proj_failures, proj_count, total


def check_fleet_summary(scripts_dir):
    indicators = []

    # OpenCode
    opencode_bin = os.getenv("OPENCODE_BIN", "/home/joao/.bun/bin/opencode")
    if not os.path.exists(opencode_bin):
        opencode_bin = shutil.which("opencode") or ""
    if opencode_bin and os.path.exists(opencode_bin):
        indicators.append("OpenCode (ready)")
    else:
        indicators.append("OpenCode (fallback)")

    # Ollama
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                indicators.append("Ollama (online)")
    except Exception:
        pass

    # API Keys
    orchestrator_dir = os.path.dirname(scripts_dir)
    env_file = os.path.join(orchestrator_dir, ".env")
    keys_found = 0
    for k in ["NVIDIA_API_KEY", "GROQ_API_KEY", "OPEN_ROUTER_API_KEY", "GITHUB_TOKEN"]:
        val = os.getenv(k, "")
        if val and not val.startswith("your_"):
            keys_found += 1
        elif os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        if line.startswith(f"{k}="):
                            v = line.split("=", 1)[1].strip()
                            if v and not v.startswith("your_"):
                                keys_found += 1
                                break
            except Exception:
                pass
    if keys_found > 0:
        indicators.append(f"API Keys ({keys_found} active)")

    return ", ".join(indicators) or "Local only"


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    target_dir = os.path.abspath(target_dir)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    orchestrator_root = os.path.dirname(scripts_dir)
    commit_hash = "unknown"
    try:
        res = subprocess.run(["git", "-C", orchestrator_root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            commit_hash = res.stdout.strip()
    except Exception:
        pass

    amase_dir = os.path.join(target_dir, ".amase")

    print(f"\n{BOLD}========================================================")
    print(" AMASE Project & Swarm Status")
    print(f" Target Directory: {target_dir}")
    print(f"========================================================{RESET}\n")

    # 0. AMASE Engine
    print(f"  {BOLD}{'AMASE Engine:':<20}{RESET} v2.1.0 ({commit_hash}) at {orchestrator_root}")

    # 1. Project Type
    ptype = detect_project_type(target_dir)
    print(f"  {BOLD}{'Project Type:':<20}{RESET} {ptype}")

    # 2. Governance
    if os.path.isdir(amase_dir):
        config_path = os.path.join(amase_dir, "config.json")
        cfg = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        sver = cfg.get("schema_version", 1)
        mode = cfg.get("mode", "autonomous")
        concurrency = cfg.get("concurrency", "sequential")
        if isinstance(concurrency, dict):
            concurrency = concurrency.get("mode", "sequential")
        tier = cfg.get("model_tier", "free")

        print(f"  {BOLD}{'Governance:':<20}{RESET} {GREEN}Ready (schema v{sver}){RESET}")
        print(f"  {BOLD}{'Execution Mode:':<20}{RESET} {mode}")
        print(f"  {BOLD}{'Concurrency:':<20}{RESET} {concurrency}")
        print(f"  {BOLD}{'Model Tier:':<20}{RESET} {tier}")
    else:
        print(f"  {BOLD}{'Governance:':<20}{RESET} {YELLOW}Not initialized (run 'amase init'){RESET}")

    # 3. Git state
    git_state = get_git_state(target_dir)
    git_color = GREEN if "Clean" in git_state else YELLOW
    print(f"  {BOLD}{'Working Tree:':<20}{RESET} {git_color}{git_state}{RESET}")

    # 4. Backlog
    next_task, pending_count, total = get_backlog_stats(target_dir)
    if total > 0:
        pct = int(((total - pending_count) / total) * 100)
        print(f"  {BOLD}{'Backlog Progress:':<20}{RESET} {total - pending_count}/{total} completed ({pct}%) | {pending_count} pending")
        if next_task:
            print(f"  {BOLD}{'Next Active Task:':<20}{RESET} {CYAN}{next_task}{RESET}")
        else:
            print(f"  {BOLD}{'Next Active Task:':<20}{RESET} {GREEN}Backlog exhausted (Scout expansion active){RESET}")
    else:
        print(f"  {BOLD}{'Backlog:':<20}{RESET} {YELLOW}No BACKLOG.md found{RESET}")

    # 5. Active Worktrees
    wts = get_active_worktrees(target_dir)
    if wts:
        print(f"  {BOLD}{'Active Worktrees:':<20}{RESET} {YELLOW}{len(wts)} active ({', '.join([os.path.basename(w.split()[0]) for w in wts])}){RESET}")
    else:
        print(f"  {BOLD}{'Active Worktrees:':<20}{RESET} {GREEN}0 active (clean){RESET}")

    # 6. Fleet Readiness
    fleet_str = check_fleet_summary(scripts_dir)
    print(f"  {BOLD}{'Fleet Readiness:':<20}{RESET} {fleet_str}")

    # 7. Retrospectives Flight Recorder
    proj_succ, proj_fail, proj_total, global_total = get_retrospectives_count(target_dir)
    if proj_total > 0:
        pct = int((proj_succ / proj_total) * 100) if proj_total > 0 else 0
        print(f"  {BOLD}{'Flight Recorder:':<20}{RESET} {proj_succ} settled, {proj_fail} incidents ({pct}% win rate) | {global_total} global")
    else:
        print(f"  {BOLD}{'Flight Recorder:':<20}{RESET} {GREEN}Clean (0 incidents logged){RESET}")

    print(f"\n{BOLD}--------------------------------------------------------{RESET}")
    if os.path.isdir(amase_dir) and total > 0:
        print(f"{GREEN}[✓] Ready to execute. Run 'amase' to start autonomous loop.{RESET}\n")
    elif not os.path.isdir(amase_dir):
        print(f"{YELLOW}[!] Run 'amase init' to scaffold governance.{RESET}\n")
    else:
        print(f"{YELLOW}[!] Create BACKLOG.md to start execution.{RESET}\n")


if __name__ == "__main__":
    main()
