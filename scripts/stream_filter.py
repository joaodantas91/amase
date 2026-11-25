#!/usr/bin/env python3
"""
AMASE Worker Terminal Stream Filter

Reads raw `agy --output-format stream-json` NDJSON (or plain text) from stdin,
writes every raw line immediately to a log file, and prints only concise,
human-readable action lines to stdout:
  [tool] <name> -> <target>
  [agent] <summary>
  [done] <status> (<duration>s)

Also provides `--last-activity <log_file>` for clean Heartbeat summaries
without leaking raw JSON fragments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, TextIO

_PATH_KEYS = (
    "Path",
    "path",
    "file_path",
    "TargetFile",
    "target_file",
    "DirectoryPath",
    "directory",
    "SearchPath",
    "SearchDirectory",
)
_CMD_KEYS = ("CommandLine", "command", "cmd")
_OTHER_KEYS = (
    "Query",
    "query",
    "Pattern",
    "pattern",
    "Url",
    "url",
    "Recipient",
    "Role",
    "Description",
    "toolSummary",
)
_NOISE_PREFIXES = (
    "warning: --mode auto is not available",
)


def _collapse_text(value: str, max_len: int = 80) -> str:
    """Collapse internal whitespace/newlines and truncate cleanly."""
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3].rstrip() + "..."


def _extract_duration(obj: dict[str, Any]) -> float | None:
    """Extract duration in seconds from common NDJSON duration fields."""
    for key in ("duration_seconds", "duration", "elapsed_seconds"):
        val = obj.get(key)
        if isinstance(val, (int, float)) and val >= 0:
            return float(val)
    for key in ("duration_ms", "elapsed_ms"):
        val = obj.get(key)
        if isinstance(val, (int, float)) and val >= 0:
            return float(val) / 1000.0
    return None


def _extract_text(obj: dict[str, Any]) -> str:
    """Extract first non-empty text summary field from an event dict."""
    for key in ("text", "summary", "message", "response", "content", "output"):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list):
            parts = []
            for item in val:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            joined = " ".join(parts).strip()
            if joined:
                return joined
    return ""


class StreamFilter:
    """Stateful formatter converting raw agy NDJSON lines into concise actions."""

    def __init__(self, cwd: str = "", start_time: float | None = None) -> None:
        self.cwd = cwd.rstrip("/") if cwd else ""
        self.start_time = start_time if start_time is not None else time.monotonic()
        self._active_tool_steps: set[int] = set()
        self.saw_done = False

    def elapsed_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.start_time)

    def _format_target(self, value: str, is_path: bool = False, max_len: int = 80) -> str:
        text = str(value).strip()
        if is_path and self.cwd:
            prefix = self.cwd + "/"
            if text.startswith(prefix):
                text = text[len(prefix):]
        return _collapse_text(text, max_len=max_len)

    def extract_tool_target(self, params: dict[str, Any]) -> str:
        """Select the most informative target parameter for a tool invocation."""
        if not isinstance(params, dict) or not params:
            return ""

        for key in _PATH_KEYS:
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return self._format_target(val, is_path=True)

        for key in _CMD_KEYS:
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return self._format_target(val, is_path=False)

        for key in _OTHER_KEYS:
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return self._format_target(val, is_path=False)

        for val in params.values():
            if isinstance(val, str) and val.strip():
                return self._format_target(val, is_path=False)
        return ""

    def _format_tool(
        self,
        name: str,
        params: dict[str, Any],
        state: str = "",
        step_index: int | None = None,
    ) -> str | None:
        state_upper = state.upper() if state else ""
        target = self.extract_tool_target(params)
        base = f"[tool] {name} -> {target}" if target else f"[tool] {name}"

        if state_upper == "ACTIVE":
            if step_index is not None:
                self._active_tool_steps.add(step_index)
            return base
        if state_upper in ("ERROR", "FAILED"):
            return f"{base} ({state_upper.lower()})"
        if state_upper == "DONE" and step_index is not None and step_index in self._active_tool_steps:
            return None
        return base

    def format_event(self, data: dict[str, Any]) -> str | None:
        """Format a parsed NDJSON event dictionary into a concise action line."""
        if not isinstance(data, dict):
            return None

        event = str(data.get("event") or data.get("type") or "").strip().lower()

        if event == "init":
            init_info = data.get("init") if isinstance(data.get("init"), dict) else data
            cwd = init_info.get("cwd")
            if isinstance(cwd, str) and cwd.strip():
                self.cwd = cwd.rstrip("/")
            model = init_info.get("model") or data.get("model")
            if isinstance(model, str) and model.strip():
                return f"[agent] init ({model.strip()})"
            return None

        if event == "step_update":
            su = data.get("step_update") if isinstance(data.get("step_update"), dict) else data
            step_type = str(su.get("step_type") or "").strip().lower()
            state = str(su.get("state") or "").strip()
            step_index = su.get("step_index") if isinstance(su.get("step_index"), int) else None

            if step_type == "user_input":
                return None

            if step_type == "tool":
                tool_info = su.get("tool_info") if isinstance(su.get("tool_info"), dict) else {}
                name = str(su.get("tool_name") or tool_info.get("name") or "tool")
                params = tool_info.get("parameters") or tool_info.get("args") or su.get("parameters") or {}
                if not isinstance(params, dict):
                    params = {}
                return self._format_tool(name, params, state=state, step_index=step_index)

            if step_type in ("agent_response", "agent_thought", "message", "assistant"):
                if state.upper() == "ACTIVE":
                    return None
                nested = su.get("agent_response") if isinstance(su.get("agent_response"), dict) else {}
                text = _extract_text(su) or _extract_text(nested)
                if text:
                    return f"[agent] {_collapse_text(text, max_len=120)}"
                return None

            if step_type in ("done", "finish", "complete"):
                self.saw_done = True
                duration = _extract_duration(su)
                if duration is None:
                    duration = self.elapsed_seconds()
                status = str(su.get("status") or state or "done").strip().lower()
                return f"[done] {status} ({duration:.1f}s)"

            return None

        if event in ("tool", "tool_use", "tool_call"):
            name = str(data.get("tool_name") or data.get("name") or "tool")
            params = data.get("parameters") or data.get("input") or data.get("args") or {}
            if not isinstance(params, dict):
                params = {}
            return self._format_tool(name, params, state=str(data.get("state") or ""))

        if event in ("agent_response", "assistant", "message", "text", "agent"):
            text = _extract_text(data)
            if text:
                return f"[agent] {_collapse_text(text, max_len=120)}"
            return None

        if event in ("result", "done", "complete", "finish"):
            self.saw_done = True
            inner = data.get(event) if isinstance(data.get(event), dict) else data
            is_err = bool(data.get("is_error") or inner.get("is_error"))
            status = inner.get("status") or inner.get("subtype") or data.get("status")
            if not status:
                status = "error" if is_err else "success"
            duration = _extract_duration(inner)
            if duration is None:
                duration = _extract_duration(data)
            if duration is None:
                duration = self.elapsed_seconds()
            return f"[done] {str(status).strip().lower()} ({duration:.1f}s)"

        if event == "error":
            self.saw_done = True
            err_obj = data.get("error")
            msg = ""
            if isinstance(err_obj, dict):
                msg = str(err_obj.get("message") or err_obj.get("type") or "")
            elif isinstance(err_obj, str):
                msg = err_obj
            if not msg:
                msg = str(data.get("message") or "")
            duration = _extract_duration(data)
            if duration is None:
                duration = self.elapsed_seconds()
            if msg.strip():
                return f"[done] error: {_collapse_text(msg, max_len=80)} ({duration:.1f}s)"
            return f"[done] error ({duration:.1f}s)"

        return None

    def format_line(self, raw_line: str) -> str | None:
        """Parse and format a single raw stream line (NDJSON or plain text)."""
        stripped = raw_line.strip()
        if not stripped:
            return None

        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return self.format_event(parsed)
            return None

        lower = stripped.lower()
        for prefix in _NOISE_PREFIXES:
            if lower.startswith(prefix):
                return None
        return f"[agent] {_collapse_text(stripped, max_len=120)}"


def filter_stream(
    input_stream: TextIO,
    output_stream: TextIO,
    log_path: str | None = None,
    append: bool = False,
    cwd: str = "",
) -> int:
    """
    Read raw lines from input_stream, write raw lines to log_path,
    and write formatted concise actions to output_stream.
    """
    flt = StreamFilter(cwd=cwd)
    emitted = 0
    log_file: TextIO | None = None

    if log_path:
        parent = os.path.dirname(os.path.abspath(log_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        mode = "a" if append else "w"
        log_file = open(log_path, mode, encoding="utf-8", errors="replace")

    try:
        for raw_line in iter(input_stream.readline, ""):
            if log_file is not None:
                log_file.write(raw_line)
                log_file.flush()

            formatted = flt.format_line(raw_line)
            if formatted:
                output_stream.write(formatted + "\n")
                output_stream.flush()
                emitted += 1
    finally:
        if log_file is not None:
            log_file.close()

    return emitted


def last_activity(log_path: str, max_lines: int = 50) -> str:
    """
    Return the latest concise human-readable activity from a worker log file,
    never returning raw JSON fragments.
    """
    if not log_path or not os.path.isfile(log_path):
        return "..."

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return "..."

    if not lines:
        return "..."

    cwd = ""
    for head_line in lines[:5]:
        s = head_line.strip()
        if s.startswith("{"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict) and obj.get("event") == "init":
                    init_info = obj.get("init") if isinstance(obj.get("init"), dict) else {}
                    if isinstance(init_info.get("cwd"), str):
                        cwd = init_info["cwd"]
                    break
            except json.JSONDecodeError:
                continue

    flt = StreamFilter(cwd=cwd)
    tail = lines[-max_lines:]
    saw_json = False

    for raw_line in reversed(tail):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("{") or stripped.startswith("["):
            saw_json = True
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                formatted = flt.format_event(parsed)
                if formatted:
                    return formatted
            continue

        lower = stripped.lower()
        if any(lower.startswith(p) for p in _NOISE_PREFIXES):
            continue
        return _collapse_text(stripped, max_len=80)

    return "working..." if saw_json else "..."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Filter raw agy stream-json NDJSON to concise terminal output while logging raw events."
    )
    parser.add_argument("log_file", nargs="?", help="Path to write raw NDJSON events")
    parser.add_argument("--log", dest="log_opt", default="", help="Log file path (alternative to positional)")
    parser.add_argument("--append", action="store_true", help="Append to log file instead of overwriting")
    parser.add_argument(
        "--last-activity",
        dest="last_activity_path",
        default="",
        help="Print latest human-readable activity summary from an existing log file and exit",
    )
    args = parser.parse_args(argv)

    if args.last_activity_path:
        print(last_activity(args.last_activity_path))
        return 0

    log_path = args.log_opt or args.log_file or None
    try:
        filter_stream(sys.stdin, sys.stdout, log_path=log_path, append=args.append)
    except (BrokenPipeError, KeyboardInterrupt):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
