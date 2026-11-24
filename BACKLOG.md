# AMASE Orchestrator Backlog

Autonomous task queue for improving the orchestrator itself.
The builder implements the first uncompleted task `[ ]`, verifies that `.amase/test-gate.sh` passes with exit code 0, and marks it `[x]`.

---

## Active Queue

- [x] **TASK-01: Deterministic One-Click Settlement Script (scripts/settle-task.sh)**
  - **Goal:** Create `scripts/settle-task.sh` that automates task verification (`.amase/test-gate.sh`), forbidden file auditing (`git diff`), fast-forward/clean merge into `main`, marking `[x]` in `BACKLOG.md`, and pruning the worktree.
  - **Files:** `scripts/settle-task.sh`, `amase`.
  - **Criteria:** Script runs with `--repo <path> --task <task-id>`, verifies exit code 0, merges cleanly, deletes worktree, and passes `.amase/test-gate.sh`.

- [x] **TASK-02: Pre-Commit Sandboxing Hook for Worker Worktrees**
  - **Goal:** In `scripts/run-task.sh`, inject an executable `.git/hooks/pre-commit` into the created worktree that rejects any commit touching forbidden files (`package.json`, `.amase/scope.md`) or adding `as any` / `@ts-ignore`.
  - **Files:** `scripts/run-task.sh`.
  - **Criteria:** Prevents workers from committing forbidden files, saving tokens and round-trips.

- [x] **TASK-03: Universal 'amase init' Project Scaffolder**
  - **Goal:** Add an `init` subcommand to the `amase` CLI (`amase init [dir]`) that auto-detects project type (Node, Python, Rust, Go) and generates `.amase/scope.md`, `.amase/discovery.md`, and `.amase/test-gate.sh` automatically.
  - **Files:** `amase`, `scripts/init-project.sh`.
  - **Criteria:** Running `amase init` on a new project creates standard boundaries and passes test gate.

- [x] **TASK-04: Token Diet Telemetry & Model Performance Ledger**
  - **Goal:** Add execution telemetry logging in `dispatch-worker.sh` and `settle-task.sh` writing to `.amase/telemetry.jsonl` (records task_id, model, duration_seconds, attempts, commit_hash, cost: 0.00).
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/settle-task.sh`.
  - **Criteria:** Telemetry is written automatically upon task settlement.

- [x] **TASK-05: Open-Source Tool Ingestion for Token Reduction & AST Symbol Indexing**
  - **Goal:** Scout, benchmark, and integrate open-source CLI utilities to drastically cut LLM token consumption in worker tasks.
  - **Candidates:** AST outline extractors (`tree-sitter`, `ctags`), token-minified packing (`repomix`), and prompt compression wrappers (`llm-compressor`, `selective-context`).
  - **Files:** `scripts/scout-tools.py`, `scripts/run-task.sh`, `docs/OPEN_SOURCE_TOOL_REGISTRY.md`.
  - **Criteria:** Produces a verified registry of $0/open-source tools that can reduce input context by at least 40% before dispatching child workers.

- [x] **TASK-06: Inject AST Symbol Outlines into generate-agent.sh Prompt Envelope**
  - **Goal:** Update `scripts/generate-agent.sh` to call `scripts/outline-ast.py` on the target repository and embed a compact symbol map into `.amase-rules.md`.
  - **Files:** `scripts/generate-agent.sh`.
  - **Criteria:** Child workers receive an accurate AST outline map, cutting read requests by >60%; passes `.amase/test-gate.sh`.

- [x] **TASK-07: Real-Time Telemetry CLI Summary (amase stats)**
  - **Goal:** Add `amase stats [dir]` command to the CLI that reads `.amase/telemetry.jsonl` and renders a clean summary table of completed tasks, models used, durations, and $0 cost.
  - **Files:** `amase`, `scripts/stats.py`.
  - **Criteria:** Running `amase stats` outputs formatted ledger table; passes `.amase/test-gate.sh`.

- [x] **TASK-08: Automatic Linter & Shellcheck Gate in test-gate.sh**
  - **Goal:** Enhance `.amase/test-gate.sh` to run `shellcheck` on bash scripts and syntax formatting checks on Python scripts, catching bash pitfalls automatically before settlement.
  - **Files:** `.amase/test-gate.sh`.
  - **Criteria:** Linter runs during test gate; clean exit code 0.

- [x] **TASK-09: Pipeline Dry-Run Simulator (amase test-wiring)**
  - **Goal:** Add `amase test-wiring` subcommand that tests worktree creation, agent directive generation, git hooks, and settlement cleanup end-to-end without spending model calls.
  - **Files:** `amase`, `scripts/test-wiring.sh`.
  - **Criteria:** Verifies complete orchestrator mechanics in <2 seconds.

- [x] **TASK-10: Token-Pruned Context Injection via AST Symbol Filter**
  - **Goal:** Enhance `scripts/outline-ast.py` with an `--include-symbols-only` flag that produces a minified context skeleton containing only relevant function signatures and interface contracts for specific target files, reducing worker prompt tokens by another 30%.
  - **Files:** `scripts/outline-ast.py`, `scripts/generate-agent.sh`.
  - **Criteria:** Generates symbol skeleton; passes `.amase/test-gate.sh`.

- [x] **TASK-11: Automatic Sentinel Remediation Injection Hook**
  - **Goal:** In `scripts/settle-task.sh`, integrate `scripts/sentinel.py` as an automatic post-merge security gate. If Sentinel reports `[CRITICAL]` or `[HIGH]` vulnerabilities, automatically prepend `TASK-SEC-01` to `BACKLOG.md`.
  - **Files:** `scripts/settle-task.sh`.
  - **Criteria:** Post-merge hook catches simulated vulnerability and writes task to backlog; passes test gate.

- [x] **TASK-12: Enhance outline-ast.py with --target-files pattern filtering**
  - **Goal:** Add a `--target-files` flag to `scripts/outline-ast.py` that accepts comma-separated glob patterns, allowing selective symbol extraction for specific file sets (e.g., only `src/` or only `*.svelte`), reducing worker prompt tokens by targeting only relevant files.
  - **Files:** `scripts/outline-ast.py`.
  - **Criteria:** `--target-files` flag parses glob patterns and filters `iter_files()` output; passes `.amase/test-gate.sh`; generates symbol skeleton for filtered files only.

- [x] **TASK-13: Extend sentinel invariant detection in settle-task.sh**
  - **Goal:** Enhance `scripts/settle-task.sh` post-merge sentinel hook to also detect common invariant violations (`as any`, `@ts-ignore`, raw hex colors in Svelte/WXT) and automatically prepend `TASK-INV-01` to `BACKLOG.md` for remediation.
  - **Files:** `scripts/settle-task.sh`.
  - **Criteria:** Post-merge hook detects invariant patterns in git diff and writes `TASK-INV-01` task to BACKLOG.md; passes `.amase/test-gate.sh`.

- [x] **TASK-14: Fix `--target-files` glob parsing in `scripts/outline-ast.py`**
  - **Goal:** Split comma-separated glob patterns and match them against file paths in `iter_files()` so `--target-files` filters correctly and reduces worker prompt tokens.
  - **Files:** `scripts/outline-ast.py`.
  - **Criteria:** `python3 scripts/outline-ast.py . --target-files 'scripts/*.py'` outputs only `scripts/*.py` files and exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-15: Inject pre-commit hook into worktrees created by `scripts/run-task.sh`**
  - **Goal:** Add the executable pre-commit hook (blocking forbidden files and `as any`/`@ts-ignore`) to `scripts/run-task.sh`, matching the mechanical enforcement already verified in `scripts/test-wiring.sh`.
  - **Files:** `scripts/run-task.sh`.
  - **Criteria:** `bash scripts/test-wiring.sh` passes end-to-end; `.amase/test-gate.sh` passes.

- [ ] **TASK-16: Context Pruner & Diff-Only Prompt Minifier**
  - **Goal:** Add a stdlib minifier that strips comments and blank lines from injected prompt rules in `generate-agent.sh`, cutting worker context 30-40%.
  - **Files:** `scripts/prune-prompt.py`, `scripts/generate-agent.sh`.
  - **Criteria:** `python3 scripts/prune-prompt.py prompts/swarm_invariants.md` exits 0 and outputs fewer bytes than input; `.amase/test-gate.sh` passes.

- [ ] **TASK-17: Fix post-merge invariant audit variable scoping in settle-task.sh**
  - **Goal:** Define `BACKLOG_FILE` and `AUDIT_FILE` before the invariant check so post-merge remediation runs without unset-variable failures and detects violations per changed file type.
  - **Files:** `scripts/settle-task.sh`.
  - **Criteria:** `bash -n scripts/settle-task.sh` exits 0 and `.amase/test-gate.sh` passes.
