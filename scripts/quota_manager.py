#!/usr/bin/env python3
"""
AMASE Quota & Rate Limit Cache Manager
Persists provider quota exhaustion state across tasks and workers with TTL.
Prevents cycling through known-exhausted models and wasting minutes.
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

DEFAULT_CACHE_DIR = os.path.expanduser("~/.amase/cache")
DEFAULT_CACHE_FILE = os.path.join(DEFAULT_CACHE_DIR, "quota.json")
DEFAULT_TTL_SECONDS = 900  # 15 minutes


def normalize_provider(model_name: str) -> str:
    """Extract canonical provider key from model string."""
    model = model_name.strip()
    if model.startswith("opencode/"):
        sub = model.split("/", 1)[1]
        if sub.endswith("-free") or "free" in sub:
            return "opencode_free"
        return "opencode"
    if model.startswith("nvidia/"):
        return "nvidia"
    if model.startswith("openrouter/"):
        sub = model.split("/", 1)[1]
        if "free" in sub:
            return "openrouter_free"
        return "openrouter"
    if model.startswith("groq/"):
        return "groq"
    if model.startswith("ollama/"):
        return "ollama"
    if "/" in model:
        return model.split("/", 1)[0]
    return model


def load_cache(cache_file: str = DEFAULT_CACHE_FILE) -> dict:
    if not os.path.exists(cache_file):
        return {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict, cache_file: str = DEFAULT_CACHE_FILE) -> None:
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    temp_file = f"{cache_file}.tmp.{os.getpid()}"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, cache_file)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        sys.stderr.write(f"Failed to save quota cache: {e}\n")


def check_quota(model_name: str, cache_file: str = DEFAULT_CACHE_FILE) -> tuple[bool, str]:
    """Returns (is_available, message). If available, returns (True, "")."""
    provider = normalize_provider(model_name)
    cache = load_cache(cache_file)
    entry = cache.get(provider)
    if not entry:
        return True, ""

    expires_at = entry.get("expires_at", 0)
    now = time.time()
    if now < expires_at:
        remaining_sec = int(expires_at - now)
        remaining_min = max(1, (remaining_sec + 59) // 60)
        reason = entry.get("reason", "quota exhausted")
        return False, f"Provider '{provider}' quota cooling down ({reason}). {remaining_min}m remaining."
    return True, ""


def record_exhaustion(model_name: str, reason: str = "quota_exhausted", ttl: int = DEFAULT_TTL_SECONDS, cache_file: str = DEFAULT_CACHE_FILE) -> None:
    provider = normalize_provider(model_name)
    cache = load_cache(cache_file)
    now = time.time()
    expires_at = now + ttl
    cache[provider] = {
        "provider": provider,
        "model": model_name,
        "exhausted_at": now,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
        "reason": reason,
    }
    save_cache(cache, cache_file)
    print(f"[i] Registered quota exhaustion for provider '{provider}' (cooldown: {ttl // 60}m).")


def clear_cache(provider: str | None = None, cache_file: str = DEFAULT_CACHE_FILE) -> None:
    if not os.path.exists(cache_file):
        print("[i] Quota cache is empty.")
        return
    if provider:
        cache = load_cache(cache_file)
        if provider in cache:
            del cache[provider]
            save_cache(cache, cache_file)
            print(f"[i] Cleared quota cooldown for '{provider}'.")
        else:
            print(f"[i] Provider '{provider}' not found in cache.")
    else:
        save_cache({}, cache_file)
        print("[i] Cleared all quota cooldowns.")


def print_status(cache_file: str = DEFAULT_CACHE_FILE) -> None:
    cache = load_cache(cache_file)
    now = time.time()
    active = {}
    for prov, data in cache.items():
        if data.get("expires_at", 0) > now:
            rem = int(data["expires_at"] - now)
            active[prov] = f"{rem // 60}m {rem % 60}s ({data.get('reason', 'exhausted')})"
    if not active:
        print("[i] All providers available (no active quota cooldowns).")
    else:
        print("[!] Active Quota Cooldowns:")
        for prov, info in active.items():
            print(f"  • {prov}: cooling down for {info}")


def main():
    parser = argparse.ArgumentParser(description="AMASE Quota Cache Manager")
    parser.add_argument("--check", metavar="MODEL", help="Check if model provider is quota-exhausted")
    parser.add_argument("--record", metavar="MODEL", help="Record quota exhaustion for model provider")
    parser.add_argument("--reason", default="rate_limit_exceeded", help="Reason for exhaustion")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS, help="TTL in seconds (default 900s / 15m)")
    parser.add_argument("--clear", nargs="?", const="", help="Clear cooldown for provider or all")
    parser.add_argument("--status", action="store_true", help="Print active quota cooldowns")
    parser.add_argument("--file", default=DEFAULT_CACHE_FILE, help="Custom cache file path")

    args = parser.parse_args()

    if args.check:
        avail, msg = check_quota(args.check, args.file)
        if not avail:
            print(f"[QUOTA_EXHAUSTED] {msg}")
            sys.exit(1)
        sys.exit(0)
    elif args.record:
        record_exhaustion(args.record, args.reason, args.ttl, args.file)
        sys.exit(0)
    elif args.clear is not None:
        prov = args.clear if args.clear != "" else None
        clear_cache(prov, args.file)
        sys.exit(0)
    elif args.status:
        print_status(args.file)
        sys.exit(0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
