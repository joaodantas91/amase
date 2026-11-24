Let me examine the diff and check for code duplication in `src/core/`.
Let me analyze this diff carefully as Sentinel.
Analysis complete. Let me assess each audit category against this diff in `scripts/settle-task.sh`:

**1. DOM injection risks:** The diff is in a bash settlement script - no `.svelte`/`.vue` files, no `innerHTML`/`outerHTML`, no unescaped templates. **Clean.**

**2. Prototype pollution/unsafe setter overrides:** The diff contains zero JavaScript. No `Object.setPrototypeOf`, `__proto__`, or unsafe setter patterns. **Clean.**

**3. Manifest V3 permission escalation:** The diff is in `scripts/settle-task.sh` - no `wxt.config.ts`, no manifest changes, no `<all_urls>` patterns. **Clean.**

**4. Code duplication (PONYTAIL Rung 2):** The diff references `$AUDIT_FILE`. The `amase` orchestrator already defines `AUDIT_FILE="$TARGET_DIR/AUDIT.md"` at `amase:38`. The original script at `settle-task.sh:144` already uses `$AUDIT_FILE`. The `src/core/` directory has no existing utilities (glob returned no files). This is not reinventing - it reuses the existing project-wide pattern. **Clean.**

**5. Missing input guards on form autofill:** The diff is a bash script for task settlement - no form fields, autofill inputs, or user input handling requiring guards. **Clean.**

All 5 categories are clean. The diff is a straightforward variable rename from hardcoded `$AUDIT.md` to the already-existing `$AUDIT_FILE` variable (consistent with line 144 and the `amase` orchestrator), introducing no new risks.
**Sentinel Audit Complete** - `scripts/settle-task.sh` diff reviewed.

**Findings across all 5 categories:**

| Category | Result |
|---|---|
| DOM injection risks (innerHTML, outerHTML, unescaped templates) | Clean - bash script, no DOM |
| Prototype pollution/unsafe setter overrides | Clean - no JavaScript in diff |
| Manifest V3 permission escalation / `<all_urls>` | Clean - no manifest changes |
| Code duplication (PONYTAIL Rung 2) | Clean - `$AUDIT_FILE` already project-wide (`amase:38`, `settle-task.sh:144`); `src/core/` has no existing utilities |
| Missing input guards on form autofill | Clean - bash settlement script, no forms |

**Verdict:** `[INFO] Core invariants verified clean.`

The diff is a straightforward refactoring: renaming hardcoded `$AUDIT.md` to the already-existing `$AUDIT_FILE` variable (consistent with line 144 and the `amase` orchestrator), introducing no new security risks or code duplication.
