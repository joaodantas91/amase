# Sentinel Audit — TASK-22 (amase config + dispatch-worker)

Scope: git diff HEAD~2..HEAD (amase, scripts/dispatch-worker.sh, .amase/config.json)

## Category Results
- [INFO] DOM injection (innerHTML/outerHTML/unescaped templates): N/A — bash-only diff, no DOM surface.
- [INFO] Prototype pollution / unsafe setter overrides: N/A — no JS/TS runtime code touched.
- [INFO] Manifest V3 permissions / broad host patterns: N/A — no manifest or extension code touched.
- [LOW] PONYTAIL Rung 2 (code duplication): CONFIG_FILE resolution block (`$TARGET_DIR/.amase/config.json` → fallback `$SCRIPT_DIR/.amase/config.json`) is duplicated in `amase` (config subcommand + main loop). Config-reading logic also duplicated in `scripts/dispatch-worker.sh`. No `src/core/` helper exists to reuse; recommend extracting a shared `resolve_config_file()` helper. Severity LOW (no security impact).
- [LOW] Missing input guards: `model_tier`, `mode`, `discovery.enabled`, `ui.builder_visible_tab` are consumed from JSON without validating allowed values; invalid values fall through to defaults via `//` but unexpected strings (e.g. `"maybe"`) are accepted and compared as strings. Recommend an allowlist check. Severity LOW.
- [LOW] JSON injection: `scripts/dispatch-worker.sh:94` builds `.amase-task-meta.json` via `printf '{"task_id": "%s", "model": "%s", ...}'` without escaping `"` or `\` in `$(basename "$WORKTREE")` / `$MODEL`; malformed meta file possible on unusual paths. Severity LOW.
- [INFO] Form autofill input guards: N/A — no form/autofill fields in this diff.

## Verification
- `bash amase config --show`: PASS (exit 0)
- `bash -n amase`: PASS
- `bash -n scripts/dispatch-worker.sh`: PASS
- `.amase/test-gate.sh`: PASS (exit 0)

## Verdict
APPROVED — no [CRITICAL] or [HIGH] findings; escalation not triggered. Low findings are hygiene-only.
" filePath">
/home/joao/dev/orchestrator/AUDIT.md