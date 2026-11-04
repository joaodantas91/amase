# UI/UX Design System Invariant (Keywords Filter Visual Baseline)

## Visual Benchmark: Keywords Filter (`Options.svelte`)
All inputs, buttons, cards, and tags across Profile Settings, Options, and Popup must follow the exact visual aesthetic of the **Keywords Filters** tab in `src/entrypoints/options/Options.svelte`.

## 1. Global CSS Tokens Only (Zero Raw Hex)
Every UI component across Popup, Options, and Content Scripts must consume centralized CSS variables:
- **Canvas & Backgrounds:** `var(--color-bg-canvas, #111111)`, `var(--color-bg-surface, #181818)`, `var(--color-bg-elevated, #1c1c1c)`, `var(--color-bg-input, #161616)`
- **Text:** `var(--color-text-primary, #eaeaea)`, `var(--color-text-secondary, #888888)`, `var(--color-text-muted, #666666)`
- **Borders:** `var(--color-border-subtle, #282828)`, `var(--color-border-default, #333333)`, `var(--color-border-hover, #444444)`, `var(--color-border-focus, #eaeaea)`
- **Accents & Destructive:** `var(--color-accent, #eaeaea)`, `var(--color-destructive, #ff6b6b)`
- **Spacing Units:** `var(--space-1, 4px)`, `var(--space-2, 8px)`, `var(--space-3, 12px)`, `var(--space-4, 16px)`, `var(--space-5, 20px)`, `var(--space-6, 24px)`, `var(--space-8, 32px)`
- **Typography:** `var(--font-xs, 11px)`, `var(--font-sm, 12px)`, `var(--font-base, 13px)`, `var(--font-md, 14px)`, `var(--font-lg, 16px)`, `var(--font-xl, 20px)`
- **Radius:** `var(--radius-sm, 4px)`, `var(--radius-md, 6px)`, `var(--radius-lg, 8px)`

**RULE:** NEVER write hardcoded hex values (e.g., `#2b2d42`, `#888`, `#333`, `#111`) directly in Svelte `<style>` tags. Always use tokens.

## 2. Reusable Component Standard (Keywords Filter Match)
- **Inputs & Selects (`.input-field`, global `input`, `select`, `textarea`):**
  - Height / Padding: compact `padding: 6px 10px`.
  - Font size: `12px` (`var(--font-sm)`).
  - Background: `var(--color-bg-input, #161616)`.
  - Border: 1px solid `var(--color-border-default, #333333)`.
  - Radius: `var(--radius-sm, 4px)`.
  - Focus: border-color to `var(--color-border-focus, #eaeaea)` with zero default browser outline.
  - Text: `var(--color-text-primary, #eaeaea)`.
- **Buttons (`.btn-primary`, `.btn-secondary`, `.btn-destructive`, `.btn-sm`, `.reset-btn`):**
  - Secondary/Reset: `padding: 3px 8px` or `6px 12px`, `font-size: 11px`/`12px`, `background: transparent`, `border: 1px solid #444`, hover `#888` / `#eaeaea`.
  - Primary: `padding: 6px 12px`, `font-size: 12px`, solid white/accent text.
  - Destructive: hover `color: var(--color-destructive, #ff6b6b)`.
- **Tags & Cards (`.tag`, `.card`):**
  - Tags match `.keyword-tag`: `background: #1c1c1c`, `border: 1px solid #333`, `border-radius: 4px`, `padding: 4px 8px`, `font-size: 12px`.
  - Cards match `.options-container` / `.profile-wrapper`: `background: #181818`, `border: 1px solid #282828`, `border-radius: 6px`, `padding: 16px`.
- **Checkboxes & Radios:**
  - `accent-color: var(--color-text-primary, #eaeaea)`. No random blue checkboxes.


## 3. Ergonomics & Accessibility Checklist
1. **Labels:** Every form field MUST have an explicit `<label for="...">` with readable contrast (4.5:1 minimum).
2. **Icons:** Use clean inline SVG (Heroicons/Lucide). NEVER use emojis as UI icons.
3. **Feedback:** Instant visual feedback on save, error, or loading (toasts, loading spinners, badge indicators).
4. **Layout:** Responsive 2-column or 1-column grid with gap tokens (`var(--space-4)`). No horizontal scroll.
