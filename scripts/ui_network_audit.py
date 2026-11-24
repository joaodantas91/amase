#!/usr/bin/env python3
"""
AMASE Asset & Console Failure Interceptor (scripts/ui_network_audit.py)

Deterministically intercepts:
1. Failed network requests (404, 500, aborted, blocked).
2. Broken <img> assets (naturalWidth === 0, failed decode).
3. Uncaught browser console errors and unhandled promise rejections.

Outputs structured JSON metrics at 0 LLM tokens.
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Any


def create_empty_report(url: str = "") -> Dict[str, Any]:
    return {
        "url": url,
        "timestamp": time.time(),
        "status": "PASS",
        "failed_requests": [],
        "broken_images": [],
        "console_errors": [],
        "summary": {
            "failed_request_count": 0,
            "broken_image_count": 0,
            "console_error_count": 0,
            "total_issues": 0
        }
    }


def record_failed_request(report: Dict[str, Any], url: str, status: int, status_text: str = "", resource_type: str = "other"):
    """Record a failed HTTP network request (4xx, 5xx, or network abort)."""
    item = {
        "url": url,
        "status": status,
        "status_text": status_text or f"HTTP {status}",
        "resource_type": resource_type
    }
    report["failed_requests"].append(item)
    update_report_summary(report)


def record_broken_image(report: Dict[str, Any], src: str, selector: str = "img"):
    """Record an <img> element that failed to render or has naturalWidth === 0."""
    item = {
        "src": src,
        "selector": selector
    }
    report["broken_images"].append(item)
    update_report_summary(report)


def record_console_error(report: Dict[str, Any], text: str, error_type: str = "error", location: str = ""):
    """Record an uncaught JS exception, console.error, or unhandled rejection."""
    item = {
        "type": error_type,
        "text": text,
        "location": location
    }
    report["console_errors"].append(item)
    update_report_summary(report)


def update_report_summary(report: Dict[str, Any]):
    f_count = len(report["failed_requests"])
    img_count = len(report["broken_images"])
    c_count = len(report["console_errors"])
    total = f_count + img_count + c_count

    report["summary"]["failed_request_count"] = f_count
    report["summary"]["broken_image_count"] = img_count
    report["summary"]["console_error_count"] = c_count
    report["summary"]["total_issues"] = total
    report["status"] = "FAIL" if total > 0 else "PASS"


def audit_url_headless(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Audit a live URL using Playwright if available, or HTTP status probing."""
    report = create_empty_report(url)

    # Try playwright python module if installed
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.on("response", lambda resp: (
                record_failed_request(
                    report,
                    resp.url,
                    resp.status,
                    resp.status_text,
                    resp.request.resource_type
                ) if resp.status >= 400 else None
            ))

            page.on("requestfailed", lambda req: (
                record_failed_request(
                    report,
                    req.url,
                    0,
                    req.failure or "Failed/Aborted",
                    req.resource_type
                )
            ))

            page.on("console", lambda msg: (
                record_console_error(
                    report,
                    msg.text,
                    "console.error" if msg.type == "error" else "console.warn"
                ) if msg.type in ("error", "warning") else None
            ))

            page.on("pageerror", lambda err: (
                record_console_error(report, str(err), "uncaught_exception")
            ))

            page.goto(url, timeout=timeout * 1000, wait_until="load")

            # Check for broken <img> elements
            broken_imgs = page.evaluate("""() => {
                return Array.from(document.images)
                    .filter(img => !img.complete || img.naturalWidth === 0)
                    .map(img => ({ src: img.src || img.getAttribute('src') || '', id: img.id || '' }));
            }""")

            for img in broken_imgs:
                record_broken_image(report, img.get("src", ""), selector=f"img#{img.get('id')}" if img.get('id') else "img")

            browser.close()
            return report
    except ImportError:
        pass
    except Exception as e:
        record_console_error(report, f"Navigation error: {e}", "navigation_failure")

    # Fallback to basic HTTP check via urllib if Playwright is not installed
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "AMASE-UI-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                record_failed_request(report, url, resp.status, resp.reason)
    except urllib.error.HTTPError as e:
        record_failed_request(report, url, e.code, e.reason)
    except Exception as e:
        record_failed_request(report, url, 0, str(e))

    return report


def run_mock_test():
    """Deterministic self-test validating error capturing, counting, and JSON schema."""
    print("[+] Running ui_network_audit.py self-test harness...")

    report = create_empty_report("http://localhost:3000/dashboard")
    assert report["status"] == "PASS"
    assert report["summary"]["total_issues"] == 0

    # Simulate 404 asset
    record_failed_request(report, "http://localhost:3000/assets/missing-logo.svg", 404, "Not Found", "image")
    # Simulate 500 API call
    record_failed_request(report, "http://localhost:3000/api/user/profile", 500, "Internal Server Error", "fetch")
    # Simulate broken image tag
    record_broken_image(report, "http://localhost:3000/images/hero.png", "img#hero-banner")
    # Simulate JS uncaught error
    record_console_error(report, "Uncaught TypeError: Cannot read properties of undefined (reading 'map')", "uncaught_exception", "main.js:42")

    assert report["status"] == "FAIL"
    assert report["summary"]["failed_request_count"] == 2
    assert report["summary"]["broken_image_count"] == 1
    assert report["summary"]["console_error_count"] == 1
    assert report["summary"]["total_issues"] == 4

    # Verify JSON serialization
    raw_json = json.dumps(report, indent=2)
    parsed = json.loads(raw_json)
    assert parsed["summary"]["total_issues"] == 4

    print("✓ Network 404/500 failure recording verified.")
    print("✓ Broken <img> asset tracking verified.")
    print("✓ Uncaught console exception tracking verified.")
    print("✓ Report JSON schema serialization verified.")
    print("[+] ui_network_audit.py self-test PASSED (exit code 0).")


def main():
    parser = argparse.ArgumentParser(description="AMASE Asset & Console Failure Interceptor")
    parser.add_argument("--url", default="", help="Target URL to audit")
    parser.add_argument("--timeout", type=int, default=15, help="Navigation timeout in seconds")
    parser.add_argument("--output", default="", help="Output JSON path")
    parser.add_argument("--mock-test", action="store_true", help="Run internal mock tests and exit")

    args = parser.parse_args()

    if args.mock_test:
        run_mock_test()
        sys.exit(0)

    if not args.url:
        parser.print_help()
        sys.exit(0)

    report = audit_url_headless(args.url, timeout=args.timeout)

    formatted = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"[+] Audit saved to {args.output}")
    else:
        print(formatted)

    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
