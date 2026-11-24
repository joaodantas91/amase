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

- [x] **TASK-16: Context Pruner & Diff-Only Prompt Minifier**
  - **Goal:** Add a stdlib minifier that strips comments and blank lines from injected prompt rules in `generate-agent.sh`, cutting worker context 30-40%.
  - **Files:** `scripts/prune-prompt.py`, `scripts/generate-agent.sh`.
  - **Criteria:** `python3 scripts/prune-prompt.py prompts/swarm_invariants.md` exits 0 and outputs fewer bytes than input; `.amase/test-gate.sh` passes.

- [x] **TASK-17: Fix post-merge invariant audit variable scoping in settle-task.sh**
  - **Goal:** Define `BACKLOG_FILE` and `AUDIT_FILE` before the invariant check so post-merge remediation runs without unset-variable failures and detects violations per changed file type.
  - **Files:** `scripts/settle-task.sh`.
  - **Criteria:** `bash -n scripts/settle-task.sh` exits 0 and `.amase/test-gate.sh` passes.

- [x] **TASK-18: Scout Backlog-Safe Emission & Dedupe**
  - **Goal:** Add a `--sanitize` stdin filter and `--emit-tasks` mode to `scripts/scout.py` that strips progress chatter, validates the markdown block, and appends only new `TASK-XX` entries to `BACKLOG.md`; update the `amase` loop to use it instead of a raw `>>` redirect that currently dumps status text into the backlog.
  - **Files:** `scripts/scout.py`, `amase`.
  - **Criteria:** `printf 'Scout: querying...\n- [ ] **TASK-99: Sample**\n  - **Goal:** g\n' | python3 scripts/scout.py --sanitize` prints only the task block and exits 0; re-emitting an existing `TASK-99` writes nothing (no duplicate); `bash -n amase` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-19: Portable Orchestrator Root Resolution in Persona Runners**
  - **Goal:** Replace hardcoded `/home/joao/dev/orchestrator/...` persona, skill, and Litellm paths in the persona runners and model switcher with a root derived from each script's own location so the orchestrator works from any checkout.
  - **Files:** `scripts/scout.py`, `scripts/sentinel.py`, `scripts/designer.py`, `scripts/switch-model`.
  - **Criteria:** `grep -rn '/home/joao/dev/orchestrator' scripts/*.py scripts/switch-model` returns no matches (exit 1); `bash -n scripts/switch-model` exits 0; `python3 -m py_compile scripts/scout.py scripts/sentinel.py scripts/designer.py` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-20: Fix ORCHESTRATOR_ROOT dirname resolution in persona runners**
  - **Goal:** In `scripts/scout.py`, `scripts/sentinel.py`, `scripts/designer.py`, and `scripts/switch-model`, fix `ORCHESTRATOR_ROOT = os.path.dirname(SCRIPTS_DIR)` so it resolves to the repo root instead of parent directory.
  - **Files:** `scripts/scout.py`, `scripts/sentinel.py`, `scripts/designer.py`, `scripts/switch-model`.
  - **Criteria:** `python3 -c "import os, sys; sys.path.insert(0, 'scripts'); from scout import ORCHESTRATOR_ROOT; assert os.path.exists(os.path.join(ORCHESTRATOR_ROOT, 'personas', 'scout.md'))"` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-21: Fix Sentinel Diff Retrieval & Add Deterministic Dry-Run**
  - **Goal:** Populate diff in scripts/sentinel.py by running git -C <target> diff <base_ref> and add a --dry-run flag that prints the assembled prompt and exits 0 without calling the fleet, so Sentinel stops crashing with NameError.
  - **Files:** scripts/sentinel.py.
  - **Criteria:** python3 scripts/sentinel.py . HEAD~1 --dry-run exits 0 and stdout contains 'DIFF TO AUDIT:' with no NameError; python3 -m py_compile scripts/sentinel.py exits 0; .amase/test-gate.sh passes.

- [x] **TASK-22: Project-Level Governance Configuration (.amase/config.json) & Manual Mode Gate**
  - **Goal:** Create default  defining  ('manual' | 'autonomous'),  ('free' | 'pro'),  ('enabled': false), and  ('builder_visible_tab': true). Update [-] Error: /home/joao is not a git repository. and  to read this config. When  is 'manual' or  is false, [-] Error: /home/joao is not a git repository. halts cleanly with exit 0 when no tasks remain. Add  command.
  - **Files:** , [-] Error: /home/joao is not a git repository., .
  - **Criteria:**  prints valid JSON; when  is manual, [-] Error: /home/joao is not a git repository. exits 0 on empty queue without invoking Scout;  exits 0;  passes.

- [x] **TASK-23: User-Directed Task Planner (amase task objective)**
  - **Goal:** Add 'amase task <objective>' subcommand and 'scripts/scout.py --objective <objective>' to decompose a user prompt into 1-2 atomic vertical slice TASK-XX blocks and append them to BACKLOG.md without unprompted auto-discovery loops.
  - **Files:** amase, scripts/scout.py.
  - **Criteria:** python3 scripts/scout.py --objective "Add metrics endpoint" --dry-run outputs formatted task block to stdout and exits 0; bash -n amase exits 0; .amase/test-gate.sh passes.

- [x] **TASK-24: Update README.md to Modern CLI Architecture & Scrub Vault References**
  - **Goal:** Scrub all hardcoded private vault references (`joao-os`, `/home/joao/dev/joao-os`) from `README.md`, `scripts/scout.py`, and `scripts/designer.py` to make the repository fully portable. Rewrite `README.md` with complete documentation for the modern `amase` CLI (`init`, `config`, `task`, `stats`, `test-wiring`, and loop execution), configuration governance (`.amase/config.json`), and $0 fleet execution.
  - **Files:** `README.md`, `scripts/scout.py`, `scripts/designer.py`.
  - **Criteria:** `grep -rn 'joao-os' README.md scripts/` returns no matches (exit 1); `python3 -m py_compile scripts/scout.py scripts/designer.py` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-25: Dedicated Visible Ptyxis Tab for Sentinel Security Audits**
  - **Goal:** Update `.amase/config.json` with `"headless_analyzers": false` and `"sentinel_visible_tab": true`. Update `scripts/settle-task.sh` to check this configuration and launch Sentinel in a visible Ptyxis terminal tab (`/usr/bin/ptyxis --tab`) displaying live audit stream to `$AUDIT_FILE`, auto-closing cleanly upon audit completion.
  - **Files:** `.amase/config.json`, `scripts/settle-task.sh`.
  - **Criteria:** `bash -n scripts/settle-task.sh` exits 0; `grep -q 'PTYXIS_BIN' scripts/settle-task.sh` exits 0; `scripts/test-wiring.sh` passes; `.amase/test-gate.sh` passes.

- [x] **TASK-26: Free Model Stall Watchdog & 120s Per-Attempt Timeout**
  - **Goal:** In `scripts/dispatch-worker.sh`, wrap each model attempt in `.amase-run.sh` with `timeout --kill-after=5s 120s` so hung sockets are immediately severed in 2 minutes. Add a 45s log inactivity watchdog in `dispatch-worker.sh` that detects zero bytes written for 45s and sends SIGKILL to force instant failover to the next fleet model.
  - **Files:** `scripts/dispatch-worker.sh`.
  - **Criteria:** `bash -n scripts/dispatch-worker.sh` exits 0; `grep -q 'timeout --kill-after' scripts/dispatch-worker.sh` exits 0; `scripts/test-wiring.sh` passes; `.amase/test-gate.sh` passes.

- [x] **TASK-27: Instant OpenCode Free-Quota Detection & Automatic Groq Direct Swap**
  - **Goal:** In `scripts/dispatch-worker.sh`, monitor `~/.local/share/opencode/log/opencode.log` to detect `"Free usage limit reached"` instantly (<1s) and SIGKILL opencode without waiting for timeouts. In `scripts/fleet.py`, add automatic stdlib `urllib.request` failover to Groq (`openai/gpt-oss-120b`) using `GROQ_API_KEY` from `.env` so child personas (Sentinel, Scout, Designer) never stall when OpenCode free pool is exhausted.
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/fleet.py`.
  - **Criteria:** `python3 -c "import sys; sys.path.insert(0, 'scripts'); from fleet import query_fleet; res = query_fleet('Say test in one word'); assert len(res) > 0"` exits 0 and returns valid text; `bash -n scripts/dispatch-worker.sh` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-28: Symlink Resolution in amase CLI Wrapper for Global PATH Execution**
  - **Goal:** Update `SCRIPT_DIR` resolution in `amase` using `readlink -f` so invoking `amase` via symlinks in `$PATH` (e.g. `~/.local/bin/amase stats`, `config`, etc.) cleanly finds orchestrator helper scripts without requiring `cd /home/joao/dev/orchestrator`.
  - **Files:** `amase`.
  - **Criteria:** `amase stats` and `amase config --show` succeed from any arbitrary directory; `bash -n amase` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-29: Persona-Model Matrix Governance & Quota Fence Enforcement**
  - **Goal:** Codify the persona-model routing matrix in `.amase/config.json` (`persona_routing`), update `litellm-config.yaml` to route Sentinel to NVIDIA NIM (128k context) and Scout to Groq (0.1s latency), configure `dispatch-worker.sh` to read `.persona_routing.builder`, and add the quota fence rule to `.agents/skills/amase-invariants/SKILL.md`.
  - **Files:** `.amase/config.json`, `config/litellm-config.yaml`, `scripts/dispatch-worker.sh`, `.agents/skills/amase-invariants/SKILL.md`.
  - **Criteria:** `jq -e '.persona_routing.builder' .amase/config.json` exits 0; `bash -n scripts/dispatch-worker.sh` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-30: Default Persona Model Fallbacks to Dedicated Fleet Aliases**
  - **Goal:** Update default fallback models in `scripts/sentinel.py` to `sentinel-fleet`, `scripts/scout.py` to `scout-fleet`, and `scripts/dispatch-worker.sh` to `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b`, completely eliminating hardcoded dependencies on exhausted community pools.
  - **Files:** `scripts/sentinel.py`, `scripts/scout.py`, `scripts/dispatch-worker.sh`.
  - **Criteria:** `python3 scripts/sentinel.py --dry-run . HEAD~1` exits 0; `python3 scripts/scout.py --objective "Test" --dry-run` exits 0; `bash -n scripts/dispatch-worker.sh` exits 0; `.amase/test-gate.sh` passes.

- [x] **TASK-31: Unified Multi-Persona Token Telemetry & Ledger Breakdown**
  - **Goal:** Update telemetry recording to track role-level tokens (`builder`, `sentinel`, `scout`, `coordinator`). Record `role`, `tokens_in`, `tokens_out`, and `model` in `.amase/telemetry.jsonl`. Update `scripts/stats.py` (`amase stats`) to render a role-based breakdown table summarizing tasks, tokens in/out, duration, and cost per persona.
  - **Files:** `scripts/stats.py`, `scripts/settle-task.sh`, `scripts/scout.py`, `scripts/fleet.py`.
  - **Criteria:** `amase stats` renders a multi-persona breakdown table displaying `ROLE`, `TOKENS IN`, `TOKENS OUT`, and `COST`; python3 -m py_compile scripts/stats.py exits 0; .amase/test-gate.sh passes.

- [x] **TASK-32: Failure Diagnostic Signatures & Post-Mortem Flight Recorder**
  - **Goal:** In `scripts/dispatch-worker.sh`, when an attempt fails or times out, analyze the run log to categorize the failure signature (`CONTEXT_BLOAT`, `COMPILER_ERROR`, `SOCKET_STALL`, `QUOTA_EXHAUSTED`). Write a structured post-mortem entry to `.amase/retrospectives.jsonl`.
  - **Files:** `scripts/dispatch-worker.sh`.
  - **Criteria:** A failed or timed-out worker run records a valid JSON record with failure signature and metrics to `.amase/retrospectives.jsonl`; bash -n scripts/dispatch-worker.sh exits 0; .amase/test-gate.sh passes.

- [x] **TASK-33: Adaptive Prompt Envelope & Self-Improvement Loop**
  - **Goal:** In `scripts/generate-agent.sh`, inspect past entries in `.amase/retrospectives.jsonl`. If previous tasks in this project suffered from `CONTEXT_BLOAT`, auto-restrict `outline-ast.py` to target files and inject targeted guardrail rules into `.amase-rules.md`.
  - **Files:** `scripts/generate-agent.sh`.
  - **Criteria:** `scripts/generate-agent.sh` dry-run with a simulated `CONTEXT_BLOAT` retrospective injects the restricted scope guardrail; .amase/test-gate.sh passes.

- [x] **TASK-34: Automated Failure Cleanup & Worktree Pruning (amase abort)**
  - **Goal:** Add `amase abort [task-id]` and automatic teardown in `dispatch-worker.sh` when all fleet models fail, cleanly unmounting the worktree (`git worktree remove --force`), pruning the branch, and resetting task state to `[ ]` without leaving dangling worktrees.
  - **Files:** `amase`, `scripts/dispatch-worker.sh`, `scripts/settle-task.sh`.
  - **Criteria:** `amase abort <task-id>` unmounts worktree and deletes branch; git status is 100% clean; .amase/test-gate.sh passes.

- [x] **TASK-35: Targeted Test Gate for Rapid Vertical Slice Verification**
  - **Goal:** In `scripts/settle-task.sh` and `.amase/test-gate.sh`, support `--diff-only` targeted testing: inspect modified files in the worktree git diff and execute only the corresponding test files first for fast sub-second gating before full suite verification.
  - **Files:** `scripts/settle-task.sh`, `.amase/test-gate.sh`.
  - **Criteria:** `bash .amase/test-gate.sh --diff-only` exits 0; bash -n scripts/settle-task.sh exits 0; .amase/test-gate.sh passes.

- [x] **TASK-36: AST Symbol Pre-Filter by Task Context Pattern**
  - **Goal:** In `scripts/generate-agent.sh` and `scripts/outline-ast.py`, parse file paths and symbol keywords from the task prompt and automatically filter the generated AST map so large codebases only inject symbols relevant to the active slice.
  - **Files:** `scripts/outline-ast.py`, `scripts/generate-agent.sh`.
  - **Criteria:** `python3 scripts/outline-ast.py . --filter "stats"` emits only symbols from stats-related files; .amase/test-gate.sh passes.

- [x] **TASK-37: System Health & Prerequisite Diagnostic (amase doctor)**
  - **Goal:** Add `amase doctor` command that runs comprehensive environment diagnostics (Git worktrees, Python 3.10+, Bun/Node runtime, LiteLLM daemon on :4000, OpenCode CLI, Ptyxis terminal, and API key availability) with colorized status report and auto-recovery hints.
  - **Files:** `amase`, `scripts/doctor.py`.
  - **Criteria:** `amase doctor` outputs formatted health check report and exits 0; python3 -m py_compile scripts/doctor.py exits 0; .amase/test-gate.sh passes.

- [x] **TASK-38: Safe Worktree Environment & Secret Isolation**
  - **Goal:** In `scripts/run-task.sh` and `scripts/dispatch-worker.sh`, safely symlink or replicate parent `.env` into child worker worktrees if present, while verifying `.gitignore` strictly prevents committing `.env` or leaking secrets to git history.
  - **Files:** `scripts/run-task.sh`, `scripts/dispatch-worker.sh`.
  - **Criteria:** Child worktree has access to parent environment variables without git tracking .env; bash -n scripts/run-task.sh exits 0; .amase/test-gate.sh passes.

- [x] **TASK-39: Accurate Builder Token Capture & Telemetry Backfill**
  - **Goal:** In `scripts/extract_tokens.py` (and `scripts/settle-task.sh`, `scripts/stats.py`), extract real builder token usage from OpenCode SQLite database (`~/.local/share/opencode/opencode.db`) matching session timestamp/directory with fallback heuristics, and backfill historical telemetry records so `amase stats` reports accurate builder token consumption.
  - **Files:** `scripts/extract_tokens.py`, `scripts/settle-task.sh`, `scripts/stats.py`.
  - **Criteria:** `python3 scripts/extract_tokens.py --help` exits 0; `amase stats` shows non-zero builder token usage; .amase/test-gate.sh passes.

- [x] **TASK-40: Global Engine Incident Telemetry & Orchestrator Ingestion Loop**
  - **Goal:** Create `scripts/engine_incident.py` to record orchestrator tool bugs and runtime limitations from any target project into central `~/.amase/engine_issues.jsonl`. When running inside orchestrator repo, update `scripts/scout.py` to ingest these engine incidents and autonomously generate `TASK-ENG-XX` self-healing tasks in orchestrator's `BACKLOG.md`.
  - **Files:** `scripts/engine_incident.py`, `scripts/scout.py`, `amase`.
  - **Criteria:** `python3 scripts/engine_incident.py --help` exits 0; simulated incident ingested into Scout as TASK-ENG block; .amase/test-gate.sh passes.

- [x] **TASK-41: Document Token Efficiency & Self-Improvement Architecture in README.md**
  - **Goal:** Update `README.md` with factual architecture sections detailing deterministic mechanical offloading (0-token operations, AST pre-filtering, context hygiene) and the self-improvement feedback loop (passive external incident logging to ~/.amase/engine_issues.jsonl and orchestrator self-healing ingestion).
  - **Files:** `README.md`.
  - **Criteria:** README.md contains Token Efficiency and Self-Improvement sections; .amase/test-gate.sh passes.

- [x] **TASK-42: Internal Script Reference & Architecture Catalog in README.md**
  - **Goal:** Document all host-side orchestration and mechanical offloading scripts in `README.md` (lifecycle, AST parsing, multi-persona agents, telemetry, diagnostics), detailing their exact role and 0-token footprint.
  - **Files:** `README.md`.
  - **Criteria:** README.md contains Internal Script Reference section with all active scripts; .amase/test-gate.sh passes.

- [x] **TASK-43: GitHub Models Auto-Connector in fleet.py & start-proxy.sh**
  - **Goal:** In `scripts/fleet.py` and `scripts/start-proxy.sh`, auto-detect `GITHUB_TOKEN` or `gh auth token` and automatically route free requests to GitHub Models (`github/gpt-4o-mini`, `github/meta-llama-3.3-70b-instruct`) as a zero-config, zero-dollar cloud fleet member.
  - **Files:** `scripts/fleet.py`, `scripts/start-proxy.sh`.
  - **Criteria:** `python3 -c "import scripts.fleet; print('fleet imported')"` exits 0; LiteLLM config includes github routing when token present; .amase/test-gate.sh passes.

- [x] **TASK-44: Local Ollama Fallback Engine in fleet.py & doctor.py**
  - **Goal:** In `scripts/fleet.py`, `scripts/doctor.py`, and `scripts/start-proxy.sh`, detect if local Ollama daemon is reachable on `localhost:11434`. If online, register `ollama/qwen2.5-coder:7b` (or active pulled models) into the fleet as an unlimited, 100% offline fallback tier; if offline, gracefully skip with auto-setup instructions in `amase doctor`.
  - **Files:** `scripts/fleet.py`, `scripts/doctor.py`, `scripts/start-proxy.sh`.
  - **Criteria:** `amase doctor` reports local Ollama status; `fleet.py` detects Ollama when active; .amase/test-gate.sh passes.

- [x] **TASK-45: Parallel Non-Conflicting Worktree Orchestration (amase parallel)**
  - **Goal:** In `amase`, `scripts/dispatch-worker.sh`, and `scripts/settle-task.sh`, add `amase parallel` to identify non-conflicting tasks in `BACKLOG.md` (orthogonal target files) and dispatch up to 2–3 isolated worktree workers concurrently in separate Ptyxis tabs.
  - **Files:** `amase`, `scripts/run-task.sh`, `scripts/settle-task.sh`.
  - **Criteria:** `amase parallel --dry-run` outputs non-conflicting task batches; .amase/test-gate.sh passes.

- [x] **TASK-46: Safe Parallel Execution Settings & Configuration (.amase/config.json & amase config)**
  - **Goal:** In `.amase/config.json`, `amase config`, and `scripts/init-project.sh`, decouple concurrency settings from orchestrator mode (`mode`: `"autonomous"` | `"interactive"`, `concurrency`: `"sequential"` | `"parallel"`, with default `concurrency: "sequential"`). Allow viewing and toggling via `amase config --concurrency` and `amase config --set-concurrency <sequential|parallel>`.
  - **Files:** `amase`, `scripts/init-project.sh`, `.amase/config.json`.
  - **Criteria:** Default concurrency is `"sequential"`; `amase config --concurrency` outputs current setting; `amase config --set-concurrency parallel` toggles properly; .amase/test-gate.sh passes.

- [x] **TASK-47: Provider-Sharded Fleet Load Balancer for Parallel Workers (Anti-429)**
  - **Goal:** In `scripts/parallel_dispatcher.py` and `scripts/fleet.py`, implement upstream provider sharding for concurrent workers. Assign distinct provider endpoints across workers in the same batch (e.g. Worker 1 -> Groq, Worker 2 -> NVIDIA NIM, Worker 3 -> GitHub Models / Ollama) so parallel workers never collide on provider rate limits or trigger 429 errors.
  - **Files:** `scripts/parallel_dispatcher.py`, `scripts/fleet.py`.
  - **Criteria:** `parallel_dispatcher.py` assigns unique provider targets per concurrent worker; .amase/test-gate.sh passes.

- [x] **TASK-48: Concurrent OpenCode SQLite Safety & Process Locking**
  - **Goal:** In `scripts/dispatch-worker.sh` and `scripts/doctor.py`, ensure concurrent OpenCode invocations do not corrupt or block `~/.local/share/opencode/opencode.db`. Verify SQLite WAL mode in `amase doctor` and add a lightweight non-blocking advisory lock on worker startup to serialize database initialization.
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/doctor.py`.
  - **Criteria:** `amase doctor` validates SQLite WAL mode for OpenCode DB; `dispatch-worker.sh` avoids SQLite collision; .amase/test-gate.sh passes.

- [x] **TASK-49: Parallel Concurrency Loop & Invariant Rule Integration**
  - **Goal:** In `amase`, `scripts/run-task.sh`, and `.agents/skills/amase-invariants/SKILL.md`, integrate parallel concurrency into the continuous orchestrator loop. When `concurrency: "parallel"` is configured and multiple pending tasks have disjoint file targets, dispatch batch via `amase parallel`; otherwise fall back safely to standard sequential dispatch (`concurrency: "sequential"`).
  - **Files:** `amase`, `scripts/run-task.sh`, `.agents/skills/amase-invariants/SKILL.md`.
  - **Criteria:** `amase` respects `concurrency: parallel` setting in loop; .amase/test-gate.sh passes.

- [x] **TASK-50: Deterministic Headless UI Layout & Collision Inspector (scripts/ui_heuristics.js)**
  - **Goal:** Create `scripts/ui_heuristics.js`, an in-browser evaluation script executed via headless Playwright/Puppeteer. Deterministically detect horizontal viewport overflows (elements spilling out of 375px mobile or desktop viewports), bounding-box collisions/overlaps between interactive elements, and zero-size click targets without sending any images or DOM dumps to LLMs (0 tokens).
  - **Files:** `scripts/ui_heuristics.js`.
  - **Criteria:** Node evaluation test detects simulated element collisions and overflow; .amase/test-gate.sh passes.

- [x] **TASK-51: Asset & Console Failure Interceptor (scripts/ui_network_audit.py)**
  - **Goal:** Create `scripts/ui_network_audit.py` to capture failed network requests (404/500), broken `<img>` assets (`naturalWidth === 0`), and unhandled browser console errors/warnings during headless page navigation, outputting structured JSON metrics at 0 LLM tokens.
  - **Files:** `scripts/ui_network_audit.py`.
  - **Criteria:** `python3 scripts/ui_network_audit.py --help` exits 0; captures mock network/console errors; .amase/test-gate.sh passes.

- [x] **TASK-52: Compact CHISLE UI Token Condenser & CLI (amase ui-check)**
  - **Goal:** Create `scripts/ui_formatter.py` and CLI subcommand `amase ui-check <url>` integrating heuristics, network audit, and a strict <150-token markdown condenser. Formats layout overlaps and broken assets into concise, actionable selector coordinates for worker agents.
  - **Files:** `scripts/ui_formatter.py`, `scripts/ui_validator.py`, `amase`.
  - **Criteria:** `amase ui-check --help` exits 0; mock failure output is under 150 tokens; .amase/test-gate.sh passes.

- [x] **TASK-53: Universal UI Validation MCP Server (scripts/ui_mcp_server.py)**
  - **Goal:** Create `scripts/ui_mcp_server.py` exposing a standard Model Context Protocol (MCP) tool (`validate_ui`) over stdio. Allows external AI orchestrators (Claude Code, Cursor, OpenCode, Windsurf, Antigravity) to inspect web pages and receive condensed CHISLE visual telemetry.
  - **Files:** `scripts/ui_mcp_server.py`.
  - **Criteria:** MCP server initializes and responds to `tools/list` and `tools/call` over stdio; .amase/test-gate.sh passes.

- [x] **TASK-54: Automatic Sleep & Lid-Close Inhibition via systemd-inhibit in amase**
  - **Goal:** In `amase`, automatically wrap continuous autonomous execution with `systemd-inhibit --what=idle:sleep:handle-lid-switch --who=AMASE --why="AMASE autonomous execution"` when available on Linux systems. Prevents laptop sleep, screen hibernation, or lid-close suspension from terminating running workers or dropping API sockets during long unattended runs.
  - **Files:** `amase`, `README.md`.
  - **Criteria:** `amase` auto-inhibits sleep when started in autonomous mode; releases cleanly on exit; .amase/test-gate.sh passes.

- [x] **TASK-55: UI Validation Fast-Gate Integration in test-gate.sh**
  - **Goal:** In `.amase/test-gate.sh` and `scripts/init-project.sh`, auto-detect frontend projects with active dev servers or static HTML files and integrate optional `amase ui-check` deterministic layout evaluation into the project test gate.
  - **Files:** `.amase/test-gate.sh`, `scripts/init-project.sh`.
  - **Criteria:** `test-gate.sh` can optionally invoke `amase ui-check` for web targets; .amase/test-gate.sh passes.

- [x] **TASK-56: OpenCode SQLite Connection Retry & WAL Pragma Auto-Tuner**
  - **Goal:** In `scripts/dispatch-worker.sh` and `scripts/doctor.py`, add automated SQLite retry loops with exponential backoff on `SQLITE_BUSY` errors, ensuring high-concurrency worker execution never drops database commits.
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/doctor.py`.
  - **Criteria:** `dispatch-worker.sh` includes retry logic for busy SQLite state; `amase doctor` verifies busy_timeout setting; .amase/test-gate.sh passes.

- [x] **TASK-57: Project Governance Auto-Heal & Versioning (Schema v2)**
  - **Goal:** Implement non-destructive auto-heal and schema v2 versioning in `scripts/init-project.sh`, `scripts/doctor.py`, and `amase` to automatically repair missing governance files and migrate configurations on the fly across external repositories.
  - **Files:** `scripts/init-project.sh`, `scripts/doctor.py`, `amase`, `.amase/config.json`, `BACKLOG.md`.
  - **Criteria:** `amase doctor --heal` passes; `scripts/init-project.sh --heal` non-destructively populates missing files without overwriting existing; test gate passes.








