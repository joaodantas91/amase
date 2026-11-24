#!/usr/bin/env python3
"""
AMASE CHISLE UI Token Condenser (scripts/ui_formatter.py)

Condenses layout heuristics (overflows, collisions) and runtime network/console
issues into a strict <150-token markdown summary tailored for LLM context windows.
Zero base64 screenshot bloat. Pure actionable selector coordinates.
"""

from typing import Dict, Any, List


def estimate_token_count(text: str) -> int:
    """Rough heuristic: ~1 token per 4 characters or 0.75 words."""
    words = text.split()
    return max(len(words), len(text) // 4)


def format_ui_report(
    url: str,
    layout_results: Dict[str, Any] = None,
    network_results: Dict[str, Any] = None,
    viewport_label: str = "375x812"
) -> str:
    """
    Format layout and network audit results into a compact <150-token string.
    """
    layout_results = layout_results or {}
    network_results = network_results or {}

    overflows: List[Dict[str, Any]] = layout_results.get("overflows", [])
    overlaps: List[Dict[str, Any]] = layout_results.get("overlaps", [])
    tiny_targets: List[Dict[str, Any]] = layout_results.get("tinyTargets", [])
    contrast_issues: List[Dict[str, Any]] = layout_results.get("contrastIssues", [])
    misalignments: List[Dict[str, Any]] = layout_results.get("misalignments", [])

    failed_requests: List[Dict[str, Any]] = network_results.get("failed_requests", [])
    broken_images: List[Dict[str, Any]] = network_results.get("broken_images", [])
    console_errors: List[Dict[str, Any]] = network_results.get("console_errors", [])

    total_issues = (
        len(overflows) + len(overlaps) + len(tiny_targets) +
        len(contrast_issues) + len(misalignments) +
        len(failed_requests) + len(broken_images) + len(console_errors)
    )

    if total_issues == 0:
        return f"[UI PASS] {url} ({viewport_label}) - Clean layout, zero collisions, zero runtime errors."

    lines = [f"[UI FAIL] {url} ({viewport_label})"]

    # 1. Layout Overflows (cap at 3)
    if overflows:
        items = [f"{o.get('selector', 'el')} (+{o.get('overflowPx', 0)}px)" for o in overflows[:3]]
        overflow_str = ", ".join(items)
        if len(overflows) > 3:
            overflow_str += f" (+{len(overflows) - 3} more)"
        lines.append(f"- Overflows: {overflow_str}")

    # 2. Element Collisions (cap at 3)
    if overlaps:
        items = [f"{o.get('elementA')} overlaps {o.get('elementB')}" for o in overlaps[:3]]
        overlap_str = "; ".join(items)
        if len(overlaps) > 3:
            overlap_str += f" (+{len(overlaps) - 3} more)"
        lines.append(f"- Collisions: {overlap_str}")

    # 3. Low Contrast (cap at 2)
    if contrast_issues:
        items = [f"{c.get('selector')} ({c.get('ratio')} < {c.get('required')})" for c in contrast_issues[:2]]
        lines.append(f"- Low Contrast: {', '.join(items)}")

    # 4. Alignment Jitter (cap at 2)
    if misalignments:
        items = [f"{m.get('elementA')} vs {m.get('elementB')} ({m.get('deltaPx')}px shift)" for m in misalignments[:2]]
        lines.append(f"- Misaligned: {', '.join(items)}")

    # 5. Tiny Targets (< 24px, cap at 2)
    if tiny_targets:
        items = [f"{t.get('selector')} ({t.get('size')})" for t in tiny_targets[:2]]
        lines.append(f"- Tiny Targets: {', '.join(items)}")

    # 6. Network failures (4xx, 5xx, cap at 3)
    if failed_requests:
        items = [f"{r.get('status', 0)} {r.get('url', '').split('/')[-1] or r.get('url')}" for r in failed_requests[:3]]
        lines.append(f"- Failed Requests: {', '.join(items)}")

    # 5. Broken Images
    if broken_images:
        items = [b.get("selector", "img") for b in broken_images[:2]]
        lines.append(f"- Broken Images: {len(broken_images)} ({', '.join(items)})")

    # 6. Console errors (cap at 2, truncated message)
    if console_errors:
        items = []
        for c in console_errors[:2]:
            txt = c.get("text", "")
            if len(txt) > 60:
                txt = txt[:57] + "..."
            items.append(txt)
        lines.append(f"- Console: {'; '.join(items)}")

    summary = "\n".join(lines)
    return summary


def run_formatter_test():
    """Verify that even with multiple failures, the condensed output stays strictly under 150 tokens."""
    mock_layout = {
        "overflows": [
            {"selector": "button#submit-btn", "overflowPx": 55},
            {"selector": "div.hero-container", "overflowPx": 24}
        ],
        "overlaps": [
            {"elementA": "button#submit-btn", "elementB": "a.cancel-link", "overlapAreaPx": 3000}
        ],
        "tinyTargets": [
            {"selector": "button.icon-close", "size": "16x16px"}
        ],
        "contrastIssues": [
            {"selector": "p.text-muted", "ratio": "2.1:1", "required": "4.5:1"}
        ],
        "misalignments": [
            {"elementA": "input#email", "elementB": "input#name", "deltaPx": 8}
        ]
    }

    mock_network = {
        "failed_requests": [
            {"status": 404, "url": "http://localhost:3000/assets/logo.svg"},
            {"status": 500, "url": "http://localhost:3000/api/user"}
        ],
        "broken_images": [
            {"selector": "img#avatar"}
        ],
        "console_errors": [
            {"text": "Uncaught TypeError: Cannot read properties of undefined"}
        ]
    }

    condensed = format_ui_report("http://localhost:3000/settings", mock_layout, mock_network, "375x812")
    token_est = estimate_token_count(condensed)

    print("[+] Formatter output:\n" + condensed)
    print(f"\n[+] Estimated token count: {token_est}")

    assert token_est < 150, f"Token count {token_est} exceeds maximum allowed budget of 150 tokens"
    assert "[UI FAIL]" in condensed
    assert "- Overflows:" in condensed
    assert "- Collisions:" in condensed
    assert "- Failed Requests:" in condensed

    clean = format_ui_report("http://localhost:3000/clean", {}, {}, "375x812")
    assert "[UI PASS]" in clean
    assert estimate_token_count(clean) < 30

    print("[+] ui_formatter.py self-test PASSED (exit code 0).")


if __name__ == "__main__":
    run_formatter_test()
