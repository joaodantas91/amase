# Sentinel Audit — `da88e51`

**Commit:** `da88e51 feat(ast): support comma-separated pattern lists and robust matching in --target-files`
**Scope:** `scripts/outline-ast.py` (+8/-1)
**Date:** 2026-11-23
**Severity scale:** `[CRITICAL]` `[HIGH]` `[MEDIUM]` `[LOW]` `[INFO]`

## Findings

### [MEDIUM] `path.lstrip("./")` is a character-set strip, not a prefix strip
`scripts/outline-ast.py:268`

`str.lstrip("./")` removes *any* leading `.` and `/` characters, not the literal `./` prefix. Confirmed behavior:

| Input | Normalized | Effect |
|---|---|---|
| `./scripts/x.py` | `scripts/x.py` | intended |
| `../scripts/x.py` | `scripts/x.py` | parent traversal erased |
| `/abs/scripts/x.py` | `abs/scripts/x.py` | root erased |
| `.github/workflows/ci.yml` | `github/workflows/ci.yml` | leading dot-dir erased |
| `.venv/lib/x.py` | `venv/lib/x.py` | leading dot-dir erased |

Impact: `--target-files` can silently mis-match — excluding intended dot-directory files or matching paths the user did not intend (the now-relative form can coincide with a real repo subpath). Read-only outline tool, so no security impact, but the filter is non-deterministic relative to its documented intent.

**Remediation spec:** replace with an explicit prefix strip, e.g. `norm_path = path[2:] if path.startswith("./") else path` (or `os.path.normpath(path)`). Verify `scripts/*.py`, `*.sh`, `./scripts/*.py`, and `.github/**` cases.

### [LOW] Basename fallback broadens matching beyond directory intent
`scripts/outline-ast.py:271`

`fnmatch(os.path.basename(norm_path), pattern)` makes every bare pattern match at any depth. `*.sh` now matches `repos/**/deploy.sh`, not just top-level scripts. Intended per help text (`'scripts/*.py,*.sh'`) but worth documenting; it can inflate symbol maps unexpectedly.

### [LOW] Empty/whitespace patterns accepted silently
`scripts/outline-ast.py:332`

`--target-files ","` yields `['', '']`, a truthy list that matches nothing, so the run exits `1` with "no supported source files found" instead of a usage error. Drop empty parts: `[p.strip() for p in ... if p.strip()]`.

## Category Results

1. **DOM injection (`innerHTML`/`outerHTML`/unescaped templates):** N/A — pure Python CLI, no DOM. `[INFO]`
2. **Prototype pollution / unsafe setters:** N/A — no JavaScript, no `__proto__`/`Object.setPrototypeOf`. `[INFO]`
3. **MV3 permission escalation / `<all_urls>`:** N/A — no `wxt.config.ts`/manifest/extension code touched. `[INFO]`
4. **Code duplication (PONYTAIL Rung 2):** No `src/core/` exists in this repo; no prior path-normalization helper to reuse. Net-new helper is justified. `[INFO]`
5. **Input guards on autofill fields:** N/A — no form/DOM autofill surface in diff. `[INFO]`

## Verdict

No `[CRITICAL]` or `[HIGH]` findings. No Orca escalation required.
One `[MEDIUM]` correctness bug (`lstrip`) — remediation spec above; regression check pending on fix branch.
