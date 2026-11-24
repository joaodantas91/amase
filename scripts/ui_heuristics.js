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

function parseColor(str) {
  if (!str) return null;
  const match = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (!match) return null;
  return {
    r: parseInt(match[1], 10),
    g: parseInt(match[2], 10),
    b: parseInt(match[3], 10),
    a: match[4] !== undefined ? parseFloat(match[4]) : 1.0
  };
}

function getLuminance(rgb) {
  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(v => {
    v = v / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function getContrastRatio(fg, bg) {
  const l1 = getLuminance(fg);
  const l2 = getLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function inspectLayout(options = {}) {
  const maxOverflowTolerance = options.overflowTolerance || 2;
  const minTargetSize = options.minTargetSize || 24;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const results = {
    viewport: { width: viewportWidth, height: viewportHeight },
    overflows: [],
    overlaps: [],
    tinyTargets: [],
    contrastIssues: [],
    misalignments: []
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

  // 4. Color contrast inspection (WCAG AA: min 4.5:1 for normal text, 3.0:1 for large text)
  const textSelector = 'p, span, h1, h2, h3, h4, h5, h6, label, button, a';
  const textEls = Array.from(document.querySelectorAll(textSelector));

  const getEffectiveBgColor = (element) => {
    let curr = element;
    while (curr && curr !== document && curr.nodeType === 1) {
      const s = window.getComputedStyle(curr);
      if (s) {
        const bg = parseColor(s.backgroundColor);
        if (bg && bg.a > 0.05) return bg;
      }
      curr = curr.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };

  for (const el of textEls) {
    if (el.offsetParent === null && el.tagName !== 'BODY') continue;
    const style = window.getComputedStyle(el);
    if (!style || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

    const text = el.textContent ? el.textContent.trim() : '';
    if (!text || text.length === 0) continue;

    const fg = parseColor(style.color);
    if (!fg) continue;

    const bg = getEffectiveBgColor(el);
    const ratio = getContrastRatio(fg, bg);

    const fontSize = parseFloat(style.fontSize) || 16;
    const fontWeight = parseInt(style.fontWeight, 10) || 400;
    const isLarge = fontSize >= 24 || (fontSize >= 18.5 && fontWeight >= 700);
    const minRatio = isLarge ? 3.0 : 4.5;

    if (ratio < minRatio) {
      results.contrastIssues.push({
        selector: getSelector(el),
        ratio: `${ratio.toFixed(1)}:1`,
        required: `${minRatio}:1`,
        text: text.length > 20 ? text.slice(0, 18) + '...' : text
      });
    }
  }

  // 5. Column misalignment & layout jitter detection for vertically adjacent form controls
  const formContainers = Array.from(document.querySelectorAll('form, .form, .form-group, fieldset, main, section, .card, body'));
  const checkedPairs = new Set();

  for (const container of formContainers) {
    const inputs = Array.from(container.querySelectorAll('input:not([type="hidden"]), select, textarea'));
    if (inputs.length < 2) continue;

    for (let i = 0; i < inputs.length - 1; i++) {
      const elA = inputs[i];
      const elB = inputs[i + 1];
      const rA = elA.getBoundingClientRect();
      const rB = elB.getBoundingClientRect();

      // Check if vertically stacked within reasonable form row distance
      if (rB.top >= rA.bottom - 5 && rB.top <= rA.bottom + 80) {
        const delta = Math.abs(rA.left - rB.left);
        // Misalignment jitter: between 3px and 24px (unintended shift)
        if (delta >= 3 && delta <= 24) {
          const key = `${getSelector(elA)}|${getSelector(elB)}`;
          if (!checkedPairs.has(key)) {
            checkedPairs.add(key);
            results.misalignments.push({
              elementA: getSelector(elA),
              elementB: getSelector(elB),
              deltaPx: Math.round(delta)
            });
          }
        }
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
      },
      {
        tagName: 'P',
        id: 'low-contrast-text',
        textContent: 'Hard to read text',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 10, y: 50, width: 200, height: 20, left: 10, right: 210, top: 50, bottom: 70 }),
        contains: () => false
      },
      {
        tagName: 'INPUT',
        id: 'input-a',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 10, y: 200, width: 200, height: 40, left: 10, right: 210, top: 200, bottom: 240 }),
        contains: () => false
      },
      {
        tagName: 'INPUT',
        id: 'input-b',
        offsetParent: {},
        getBoundingClientRect: () => ({ x: 18, y: 250, width: 200, height: 40, left: 18, right: 218, top: 250, bottom: 290 }),
        contains: () => false
      }
    ];

    global.window = mockWindow;
    global.document = {
      body: {},
      querySelectorAll: (sel) => {
        if (sel === 'body *') return elements;
        if (sel.includes('button') || sel.includes('input') || sel.includes('text')) {
          return elements.filter(e => ['BUTTON', 'A', 'INPUT', 'P'].includes(e.tagName));
        }
        if (sel.includes('form') || sel.includes('body')) {
          return [{
            querySelectorAll: () => elements.filter(e => e.tagName === 'INPUT')
          }];
        }
        return [];
      }
    };
    global.window.getComputedStyle = (el) => {
      if (el && el.id === 'low-contrast-text') {
        return {
          display: 'block', visibility: 'visible', opacity: '1',
          color: 'rgb(200, 200, 200)',
          backgroundColor: 'rgb(255, 255, 255)',
          fontSize: '14px', fontWeight: '400'
        };
      }
      return {
        display: 'block', visibility: 'visible', opacity: '1',
        color: 'rgb(0, 0, 0)',
        backgroundColor: 'rgb(255, 255, 255)',
        fontSize: '16px', fontWeight: '400'
      };
    };

    const results = inspectLayout();
    console.log('Results:', JSON.stringify(results, null, 2));

    const hasOverflow = results.overflows.some(o => o.selector === '#submit-btn' && o.overflowPx > 50);
    const hasOverlap = results.overlaps.some(o => o.elementA === '#submit-btn' && o.elementB === '#cancel-link');
    const hasTiny = results.tinyTargets.some(t => t.selector === '#icon-btn');
    const hasContrast = results.contrastIssues.some(c => c.selector === '#low-contrast-text');
    const hasMisalignment = results.misalignments.some(m => m.elementA === '#input-a' && m.elementB === '#input-b');

    if (hasOverflow && hasOverlap && hasTiny && hasContrast && hasMisalignment) {
      console.log('✓ Viewport overflow detected correctly.');
      console.log('✓ Element collision/overlap detected correctly.');
      console.log('✓ Tiny click target detected correctly.');
      console.log('✓ Low WCAG color contrast detected correctly.');
      console.log('✓ Form column misalignment detected correctly.');
      console.log('[+] ui_heuristics.js self-test PASSED (exit code 0).');
      process.exit(0);
    } else {
      console.error('[-] Self-test assertions failed:', { hasOverflow, hasOverlap, hasTiny, hasContrast, hasMisalignment });
      process.exit(1);
    }
  } else {
    console.log('Usage: node scripts/ui_heuristics.js --test');
  }
}

module.exports = { inspectLayout };
