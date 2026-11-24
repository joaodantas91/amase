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

- [ ] **TASK-09: Pipeline Dry-Run Simulator (amase test-wiring)**
  - **Goal:** Add `amase test-wiring` subcommand that tests worktree creation, agent directive generation, git hooks, and settlement cleanup end-to-end without spending model calls.
  - **Files:** `amase`, `scripts/test-wiring.sh`.
  - **Criteria:** Verifies complete orchestrator mechanics in <2 seconds.
