# UI/UX Design System Invariant (ui-ux-pro-max)

## 1. Global CSS Tokens Only (Zero Raw Hex)
Every UI component across Popup, Options, and Content Scripts must consume centralized CSS variables:
- **Backgrounds:** `var(--color-background, #0F172A)`, `var(--color-card, #111827)`, `var(--color-muted, #1E293B)`
- **Text:** `var(--color-foreground, #F8FAFC)`, `var(--color-muted-foreground, #CBD5E1)`
- **Borders & Rings:** `var(--color-border, #334155)`, `var(--color-ring, #0369A1)`
- **Accents & Brand:** `var(--color-primary, #0369A1)`, `var(--color-secondary, #0EA5E9)`, `var(--color-accent, #16A34A)`
- **Destructive/Alert:** `var(--color-destructive, #DC2626)`
- **Spacing Units:** `var(--space-1, 4px)`, `var(--space-2, 8px)`, `var(--space-3, 12px)`, `var(--space-4, 16px)`, `var(--space-6, 24px)`
- **Radius:** `var(--radius-sm, 4px)`, `var(--radius-md, 8px)`, `var(--radius-lg, 12px)`

**RULE:** NEVER write hardcoded hex values (e.g., `#2b2d42`, `#888`, `#333`, `#111`) directly in Svelte `<style>` tags. Always use tokens.

## 2. Reusable Component Standard
Every input, button, select, and card MUST look and feel consistent across all surfaces:
- **Inputs & Selects (`.input-field`):**
  - Height: min 38px (touch target friendly).
  - Background: `var(--color-muted)`.
  - Border: 1px solid `var(--color-border)`.
  - Radius: `var(--radius-sm)`.
  - Focus: 2px ring with `var(--color-ring)` and zero default browser outline.
  - Text: `var(--color-foreground)`.
- **Buttons (`.btn-primary`, `.btn-secondary`, `.btn-destructive`):**
  - Padding: 8px 16px.
  - Font weight: 500.
  - Cursor: `cursor: pointer`.
  - Transition: `150ms ease`.
  - Hover: subtle opacity or brightness shift, never layout shift.
- **Cards (`.card`):**
  - Background: `var(--color-card)`.
  - Border: 1px solid `var(--color-border)`.
  - Padding: `var(--space-4)`.
  - Border radius: `var(--radius-md)`.

## 3. Ergonomics & Accessibility Checklist
1. **Labels:** Every form field MUST have an explicit `<label for="...">` with readable contrast (4.5:1 minimum).
2. **Icons:** Use clean inline SVG (Heroicons/Lucide). NEVER use emojis as UI icons.
3. **Feedback:** Instant visual feedback on save, error, or loading (toasts, loading spinners, badge indicators).
4. **Layout:** Responsive 2-column or 1-column grid with gap tokens (`var(--space-4)`). No horizontal scroll.
