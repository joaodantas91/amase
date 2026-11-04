# INVARIANTS
1. STRICT TYPES: Never use 'as any' or '@ts-ignore'. All types must be strictly typed or use type narrowing (typeof, instanceof, in).
2. PONYTAIL: Standard library & native APIs first. Zero unnecessary npm packages. WXT + Svelte 5 runes ($state, $derived, $props). Zero code duplication: search existing helpers in src/core/ before writing new ones.
3. UI/UX DESIGN SYSTEM (ui-ux-pro-max): Use centralized CSS tokens (tokens.css / components.css). Zero hardcoded raw hex colors in components. All inputs, buttons, cards must follow reusable component classes. High-contrast dark mode, explicit labels, SVG icons (no emoji).
4. CAVEMAN: Answer first: [thing] [action] [reason]. [next step]. Zero pleasantries. Paths, commands, errors verbatim.
5. CHISLE: Read line ranges only. Suppress passing test dumps.
6. QUALITY GATE: Never mark done until bunx vitest run and bun run check pass with exit code 0 and zero errors.
7. GIT COMMIT: Always git add and commit before reporting done.
