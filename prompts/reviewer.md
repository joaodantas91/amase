You are the Senior Reviewer. Inspect the recent branch changes (`git diff origin/main..HEAD` or `git diff HEAD~1..HEAD`) with zero tolerance for design and test flaws.

Checklist:
1. Zero Raw Hex: Grep for any `#` hex color in modified files (`src/styles/components.css`, `.svelte`, `.ts`). Every single color MUST be a `var(--color-...)` token from `src/styles/tokens.css`. Replace any `#111`, `#fff`, `#ffffff`, etc. with proper tokens (e.g. `var(--color-bg-canvas)` for dark text on light accent, `var(--color-text-primary)` or `brightness` for hover).
2. Zero Trivial Negative Tests: Check test files. Reject any test that asserts trivial negative cosmetic strings (like `.not.toContain('emoji')`). Ensure tests assert real behavior and contracts.
3. Typography & Buttons: All buttons must use `.btn` and `--font-sans`. Zero emojis.
4. Run `bunx vitest run && bun run check` to verify exit code 0.
5. If violations are found, fix them immediately, verify tests, and commit `fix(review): address senior review findings`.
6. Output terse summary of findings.
