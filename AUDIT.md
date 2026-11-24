# Sentinel Audit Report

Target: scripts/settle-task.sh (TASK-25 visible Ptyxis tab + headless fallback)
Base: HEAD~1

## Findings

[MEDIUM] Shell injection surface in visible Ptyxis tab launch: `$ORCHESTRATOR_DIR`, `$TARGET_REPO`, and `$AUDIT_FILE` are interpolated into a double-quoted `bash -c` argument wrapped in single quotes. A path containing a single quote or shell metacharacter can break quoting and execute arbitrary commands. Remediation: pass paths via environment variables or argv instead of string interpolation, or strictly validate/escape inputs.

[LOW] Background process leak on timeout: if `DONE_FLAG` never appears, polling exits after 300s but the ptyxis/sentinel child may keep running and writing to `AUDIT_FILE`. Remediation: track PID and terminate process group on timeout.

[LOW] Duplicate constant: `PTYXIS_BIN='/usr/bin/ptyxis'` is hardcoded in both `scripts/settle-task.sh` and `scripts/dispatch-worker.sh`. Remediation: centralize in a shared helper under scripts/.

[INFO] DOM injection, prototype pollution, Manifest V3 permissions, src/core duplication, and form autofill guards: not applicable to this shell-script diff.

## Verification
- bash -n scripts/settle-task.sh: PASS
- .amase/test-gate.sh: PASS (exit 0)
