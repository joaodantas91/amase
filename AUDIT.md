Looking at the diff, I need to audit this against the 5 Sentinel responsibilities. Let me first explore the codebase to understand existing utilities.
Let me check the existing AUDIT.md and scripts for any similar utilities.
Looking at the diff - changes to `scripts/generate-agent.sh` (piping SCOPE_CONTENT and PERSONA_CONTENT through `prune-prompt.py`) and a new `scripts/prune-prompt.py` that removes markdown comments, strips trailing whitespace, and collapses blank lines.

**Audit against 5 Sentinel responsibilities:**

1. **DOM injection risks** - [INFO] No innerHTML, outerHTML, or unescaped templates in these shell/Python scripts.
2. **Prototype pollution / unsafe setters** - [INFO] No JavaScript prototype manipulation; the Python script uses only standard library regex/text processing.
3. **MV3 permission escalation / `<all_urls>`** - [INFO] Not a WXT project; no manifest changes.
4. **Code duplication (PONYTAIL Rung 2)** - [INFO] `src/core/` doesn't exist in this orchestrator framework; `prune-prompt.py` is a new utility without an existing counterpart to duplicate.
5. **Missing input guards on form autofill** - [INFO] No form autofill fields in these scripts.

The `prune-prompt.py` script is benign - uses only `sys`, `re` from stdlib; regex `<!--.*?-->` with `re.DOTALL` for comment removal; `rstrip()` for whitespace; blank-line collapsing. No unsafe eval/exec, no prototype risks.

[INFO]
