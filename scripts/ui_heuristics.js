#!/usr/bin/env node
/**
 * AMASE UI Layout & Collision Inspector (scripts/ui_heuristics.js)
 * 
 * Deterministic, zero-token in-browser evaluation script for headless Playwright/Puppeteer.
 * Inspects the live DOM for:
 * 1. Viewport Overflows (horizontal scroll violations on mobile/desktop)
 * 2. Interactive Element Collisions (buttons/links overlapping each other)
 * 3. Tiny / Zero-size click targets (< 24px)
 * 
 * Can be passed to page.evaluate() or executed directly via Node (--test).
 */

function inspectLayout(options = {}) {
  const maxOverflowTolerance = options.overflowTolerance || 2;
  const minTargetSize = options.minTargetSize || 24;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const results = {
    viewport: { width: viewportWidth, height: viewportHeight },
    overflows: [],
    overlaps: [],
    tinyTargets: []
  };

  const getSelector = (el) => {
    if (!el || el === document.body) return 'body';
    if (el.id) return `#${el.id}`;
    let name = el.tagName.toLowerCase();
    if (el.className && typeof el.className === 'string') {
      const cls = el.className.trim().split(/\s+/).filter(c => !c.includes(':')).slice(0, 2).join('.');
      if (cls) name += `.${cls}`;
    }
    return name;
  };

  // 1. Check for elements overflowing horizontal viewport
  const allElements = document.querySelectorAll('body *');
  for (const el of allElements) {
    if (el.offsetParent === null && el.tagName !== 'BODY') continue; // invisible
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.right > viewportWidth + maxOverflowTolerance) {
      const overflowPx = Math.round(rect.right - viewportWidth);
      results.overflows.push({
        selector: getSelector(el),
        tag: el.tagName.toLowerCase(),
        overflowPx,
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
      });
    }
  }

  // 2. Check interactive elements for collisions and tiny click targets
  const interactiveSelector = 'button, a[href], input:not([type="hidden"]), select, textarea, [role="button"], [tabindex]:not([tabindex="-1"])';
  const interactiveEls = Array.from(document.querySelectorAll(interactiveSelector));

  const validTargets = [];
  for (const el of interactiveEls) {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 && rect.height <= 0) continue;

    const selector = getSelector(el);

    // Tiny target check
    if (rect.width < minTargetSize || rect.height < minTargetSize) {
      results.tinyTargets.push({
        selector,
        size: `${Math.round(rect.width)}x${Math.round(rect.height)}px`,
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
      });
    }

    validTargets.push({ el, selector, rect });
  }

  // 3. Collision detection between interactive elements
  for (let i = 0; i < validTargets.length; i++) {
    for (let j = i + 1; j < validTargets.length; j++) {
      const a = validTargets[i];
      const b = validTargets[j];

      // Ignore parent-child relationships
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;

      const rA = a.rect;
      const rB = b.rect;

      const xOverlap = Math.max(0, Math.min(rA.right, rB.right) - Math.max(rA.left, rB.left));
      const yOverlap = Math.max(0, Math.min(rA.bottom, rB.bottom) - Math.max(rA.top, rB.top));
      const overlapArea = xOverlap * yOverlap;

      // Report if overlap area is significant (> 16px)
      if (overlapArea > 16) {
        results.overlaps.push({
          elementA: a.selector,
          elementB: b.selector,
          overlapAreaPx: Math.round(overlapArea),
          rectA: { x: Math.round(rA.x), y: Math.round(rA.y), width: Math.round(rA.width), height: Math.round(rA.height) },
          rectB: { x: Math.round(rB.x), y: Math.round(rB.y), width: Math.round(rB.width), height: Math.round(rB.height) }
        });
      }
    }
  }

  return results;
}

// Self-test simulation harness if executed via CLI
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.includes('--test') || args.includes('-t')) {
    console.log('[+] Running ui_heuristics.js self-test harness...');

    // Mock minimal DOM environment
    const mockWindow = { innerWidth: 375, innerHeight: 812 };
    const elements = [
      {
        tagName: 'BUTTON',
        id: 'submit-btn',
        className: 'btn primary',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 10, y: 100, width: 420, height: 40, left: 10, right: 430, top: 100, bottom: 140 }),
        contains: () => false
      },
      {
        tagName: 'A',
        id: 'cancel-link',
        className: 'link',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 50, y: 110, width: 100, height: 30, left: 50, right: 150, top: 110, bottom: 140 }),
        contains: () => false
      },
      {
        tagName: 'BUTTON',
        id: 'icon-btn',
        className: 'btn-icon',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 10, y: 10, width: 16, height: 16, left: 10, right: 26, top: 10, bottom: 26 }),
        contains: () => false
      }
    ];

    global.window = mockWindow;
    global.document = {
      body: {},
      querySelectorAll: (sel) => {
        if (sel === 'body *') return elements;
        if (sel.includes('button')) return elements;
        return [];
      }
    };
    global.window.getComputedStyle = () => ({ display: 'block', visibility: 'visible', opacity: '1' });

    const results = inspectLayout();
    console.log('Results:', JSON.stringify(results, null, 2));

    const hasOverflow = results.overflows.some(o => o.selector === '#submit-btn' && o.overflowPx > 50);
    const hasOverlap = results.overlaps.some(o => o.elementA === '#submit-btn' && o.elementB === '#cancel-link');
    const hasTiny = results.tinyTargets.some(t => t.selector === '#icon-btn');

    if (hasOverflow && hasOverlap && hasTiny) {
      console.log('✓ Viewport overflow detected correctly.');
      console.log('✓ Element collision/overlap detected correctly.');
      console.log('✓ Tiny click target detected correctly.');
      console.log('[+] ui_heuristics.js self-test PASSED (exit code 0).');
      process.exit(0);
    } else {
      console.error('[-] Self-test assertions failed:', { hasOverflow, hasOverlap, hasTiny });
      process.exit(1);
    }
  } else {
    console.log('Usage: node scripts/ui_heuristics.js --test');
  }
}

module.exports = { inspectLayout };
