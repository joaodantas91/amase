# Sentinel Audit — scripts/sentinel.py (commit 4705f5b)

Scope: diff 4790161..68e6f5a (diff retrieval + `--dry-run` + prompt duplication).
Regression: `python3 -m py_compile scripts/sentinel.py` → OK. Prior `NameError: diff` fixed.

## Findings

- [HIGH] S-01 Dry-run positional parsing broken — `scripts/sentinel.py:61-63`. `"--dry-run" in sys.argv` is checked but not stripped; `sys.argv[1]` becomes the flag itself. `sentinel.py --dry-run /repo HEAD~1` sets `target="--dry-run"`, `base="/repo"` → `git -C --dry-run` fails → empty diff → model can emit "Core invariants verified clean". Only works when flag is last. Fix: filter flag out of args (`args=[a for a in sys.argv[1:] if a!="--dry-run"]`).
- [HIGH] S-02 PONYTAIL Rung 2 duplication — `scripts/sentinel.py:66-88` duplicates the diff-collection block (`:23-30`) and the entire prompt template (`:35-48`). Violates zero-duplication invariant; the two copies already diverged (dry-run omits `[MEDIUM]` tag from its contract line). Fix: `run_audit(target, base, dry_run=False)` returning the prompt; print it in dry-run.
- [MEDIUM] S-03 Git argument injection — `scripts/sentinel.py:25,69`. `base_ref`/`target_dir` from argv are passed as git operands. No `shell=True` (good, not RCE), but a ref like `--output=/path` or `--ext-diff` is parsed as a git option; `target_dir` after `-C` likewise. Fix: validate ref via `git rev-parse --verify` and pass `--` before the ref (`... "diff", "--", base_ref`).
- [MEDIUM] S-04 Silent failure → false-clean gate — `scripts/sentinel.py:29-30,73-74`. Bare `except Exception` maps timeout/non-repo/git error to `diff=""`, then audits nothing and may sign off clean. Fix: capture `returncode`/stderr, abort with non-zero exit instead of producing an empty prompt.
- [MEDIUM] S-05 Contract not enforced — `scripts/sentinel.py:4,53`. Docstring/persona claim report is written to `AUDIT.md`; code only `print()`s. Prior AUDIT.md held a stale traceback. Fix: write `AUDIT.md` (or have Orchestrator persist) before exit.
- [LOW] S-06 Redundant import — `scripts/sentinel.py:90`. `import sys as _sys` after `import sys` at `:9`; use `sys.exit(0)`.
- [LOW] S-07 Dead read — `scripts/sentinel.py:64-65`. `sentinel_prompt` loaded in dry-run, never used.
- [LOW] S-08 Raw diff to stdout — `scripts/sentinel.py:89`. `print(user_prompt)` dumps up to 4KB of diff into CI/console logs; redact or gate behind `--verbose`.

## Not Applicable
- [INFO] DOM injection (innerHTML/outerHTML/unescaped templates): N/A — diff touches only Python tooling, no Svelte/TS/HTML.
- [INFO] Prototype pollution / unsafe setter overrides: N/A — no JS/native setter code in diff.
- [INFO] Manifest V3 permission escalation / `<all_urls>`: N/A — no `wxt.config.ts` or manifest changes.
- [INFO] Missing input guards on autofill fields: N/A — no content-script/form code in diff.

## Escalation
[HIGH] S-01 and S-02 require Orchestrator escalation. No `run_id` present in environment (`orca` available, `RUN_ID`/`AMASE_*` unset), so `orca orchestration send --to run:<run_id>` was not dispatched. Awaiting run id.

## Verdict
REJECTED — 2 × [HIGH], fix S-01/S-02 before merge; S-03/S-04 gate integrity should follow.
