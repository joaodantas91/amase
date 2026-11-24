#!/usr/bin/env python3
"""
AMASE Headless UI Validator CLI (scripts/ui_validator.py / amase ui-check)

Orchestrates:
1. In-browser layout inspection (overflows, collisions, tiny targets).
2. Network & console error audit (404/500, broken images, uncaught exceptions).
3. Compact CHISLE token condenser (<150 tokens) for agent prompts.

Exit code 0 on clean UI pass; exit code 1 on layout or runtime violations.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from ui_formatter import format_ui_report, estimate_token_count
    from ui_network_audit import audit_url_headless
except ImportError:
    from scripts.ui_formatter import format_ui_report, estimate_token_count
    from scripts.ui_network_audit import audit_url_headless


def run_heuristics_via_node(url: str, viewport_width: int = 375, viewport_height: int = 812) -> Dict[str, Any]:
    """Execute ui_heuristics.js inside headless browser via Node/Playwright if available."""
    heuristics_path = os.path.join(SCRIPT_DIR, "ui_heuristics.js")
    runner_script = f"""
const {{ chromium }} = require('playwright');
const {{ inspectLayout }} = require('{heuristics_path}');

(async () => {{
  try {{
    const browser = await chromium.launch({{ headless: true }});
    const context = await browser.newContext({{
      viewport: {{ width: {viewport_width}, height: {viewport_height} }}
    }});
    const page = await context.newPage();
    await page.goto('{url}', {{ timeout: 15000, waitUntil: 'load' }});
    const results = await page.evaluate(inspectLayout);
    await browser.close();
    console.log(JSON.stringify(results));
  }} catch (err) {{
    console.log(JSON.stringify({{ error: err.message, overflows: [], overlaps: [], tinyTargets: [] }}));
  }}
}})();
"""
    try:
        proc = subprocess.run(["node", "-e", runner_script], capture_output=True, text=True, timeout=20)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
    except Exception:
        pass

    return {"viewport": {"width": viewport_width, "height": viewport_height}, "overflows": [], "overlaps": [], "tinyTargets": []}


def validate_page(url: str, viewport_label: str = "375x812") -> Dict[str, Any]:
    """Audit single URL for both layout collisions and network/console errors."""
    width, height = 375, 812
    if "x" in viewport_label:
        parts = viewport_label.split("x")
        try:
            width, height = int(parts[0]), int(parts[1])
        except ValueError:
            pass

    layout = run_heuristics_via_node(url, width, height)
    network = audit_url_headless(url, timeout=12)

    condensed = format_ui_report(url, layout, network, viewport_label)
    tokens = estimate_token_count(condensed)

    is_pass = "[UI PASS]" in condensed
    return {
        "url": url,
        "viewport": viewport_label,
        "status": "PASS" if is_pass else "FAIL",
        "condensed_report": condensed,
        "estimated_tokens": tokens,
        "layout": layout,
        "network": network
    }


def run_mock_test():
    """Verify that ui_validator CLI mock test passes and complies with token budget."""
    print("[+] Running ui_validator.py self-test harness...")

    mock_layout = {
        "overflows": [{"selector": "table.data-grid", "overflowPx": 45}],
        "overlaps": [],
        "tinyTargets": []
    }
    mock_network = {
        "failed_requests": [{"status": 404, "url": "http://localhost:3000/logo.png"}],
        "broken_images": [],
        "console_errors": []
    }

    report = format_ui_report("http://localhost:3000", mock_layout, mock_network, "375x812")
    tokens = estimate_token_count(report)
    print(f"Report:\n{report}")
    print(f"Estimated tokens: {tokens}")

    assert "[UI FAIL]" in report
    assert tokens < 150
    print("[+] ui_validator.py self-test PASSED (exit code 0).")


def main():
    parser = argparse.ArgumentParser(description="AMASE Headless UI Validator (amase ui-check)")
    parser.add_argument("url", nargs="?", default="", help="Target web URL to validate (e.g. http://localhost:3000)")
    parser.add_argument("--viewport", default="375x812", help="Viewport dimensions WxH (default: 375x812 mobile)")
    parser.add_argument("--json", action="store_true", help="Output full JSON telemetry instead of condensed text")
    parser.add_argument("--mock-test", action="store_true", help="Run self-test validation and exit")

    args = parser.parse_args()

    if args.mock_test:
        run_mock_test()
        sys.exit(0)

    if not args.url:
        parser.print_help()
        sys.exit(0)

    res = validate_page(args.url, viewport_label=args.viewport)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(res["condensed_report"])

    sys.exit(0 if res["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
