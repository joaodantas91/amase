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

- [x] **TASK-58: Retrospective Flight Recorder Precision & Local Ollama OpenCode Fleet Registration**
  - **Goal:** Enhance `scripts/diagnose-failure.py` to classify TypeScript / framework test gate errors (`svelte-check`, `tsc`, `ELIFECYCLE`) as `COMPILER_ERROR` directly from worktrees, add auto-commit test verification in `scripts/dispatch-worker.sh`, and register local Ollama (`qwen2.5-coder:14b`) in `~/.config/opencode/opencode.json`.
  - **Files:** `scripts/diagnose-failure.py`, `scripts/dispatch-worker.sh`, `amase`, `BACKLOG.md`.
  - **Criteria:** `diagnose-failure.py` accurately identifies compile/gate errors; `opencode models` lists `ollama/qwen2.5-coder:14b`; test-gate passes.

- [x] **TASK-59: Decouple Language Dependencies & Universal Manifest Detection**
  - **Goal:** Remove hardcoded Node/WXT assumptions from `generate-agent.sh`, `run-task.sh`, and `test-wiring.sh`. Dynamically resolve project manifest (`Cargo.toml`, `pyproject.toml`, `go.mod`, `package.json`) to protect against unauthorized dependency modifications in pre-commit hooks and worker prompts.
  - **Files:** `scripts/generate-agent.sh`, `scripts/run-task.sh`, `scripts/test-wiring.sh`, `BACKLOG.md`.
  - **Criteria:** Script syntax passes; prompt generation is language-agnostic; test-gate passes.

- [x] **TASK-60: Root CLI Help Menu & Version Flags (--help, --version)**
  - **Goal:** Add structured help menu (`amase --help`, `amase -h`) and version flag (`amase --version`, `amase -v`) displaying command usage, subcommands, sleep inhibition flags, examples, and documentation links without triggering bash fallback errors.
  - **Files:** `amase`, `BACKLOG.md`.
  - **Criteria:** `amase --help` and `amase -v` exit 0 with formatted usage; test gate passes.

- [x] **TASK-61: Dedicated Instant Pre-Flight Inspection CLI (amase status)**
  - **Goal:** Add `amase status [dir]` displaying project type, governance schema version, backlog progress (completed/pending/next task), working tree cleanliness, active worktrees, and model fleet readiness in a single clean 1-read screen.
  - **Files:** `scripts/status.py`, `amase`, `BACKLOG.md`.
  - **Criteria:** `amase status` and `amase status <dir>` exit 0 with unified telemetry; test gate passes.

- [x] **TASK-62: Auto-Commit Dirty Governance State on Main Before Worktree Branching**
  - **Goal:** In `amase`, `scripts/run-task.sh`, and `scripts/parallel_dispatcher.py`, automatically stage and commit uncommitted governance files (`BACKLOG.md`, `.amase/*`) on `main` before branching worktrees. Prevents worktrees from missing newly added backlog tasks and eliminates merge conflicts during task settlement.
  - **Files:** `amase`, `scripts/run-task.sh`, `scripts/parallel_dispatcher.py`, `BACKLOG.md`.
  - **Criteria:** Uncommitted changes to `BACKLOG.md` on main are auto-synced prior to worktree creation; test gate passes.

- [x] **TASK-63: Autonomous Coordinator Guardrails in Global Protocol (GEMINI.md)**
  - **Goal:** Update global protocol in `~/.gemini/config/GEMINI.md` to instruct AI coordinators to use `amase status` and `amase` directly instead of manually inspecting internal orchestrator implementation scripts (`run-task.sh`, `settle-task.sh`, `amase` source) or manually managing git branches.
  - **Files:** `/home/joao/.gemini/config/GEMINI.md`, `README.md`, `BACKLOG.md`.
  - **Criteria:** Protocol explicitly guides clean agents to run `amase status` / `amase` without token-wasting manual script reads.

- [x] **TASK-64: Centralize Retrospective Flight Recorder (~/.amase/retrospectives.jsonl)**
  - **Goal:** Unify scattered local `.amase/retrospectives.jsonl` files into a single persistent global registry at `~/.amase/retrospectives.jsonl` with project tags. Eliminates untracked file pollution across repositories, enables cross-project learned guardrails in `generate-agent.sh`, and integrates with `amase status` and `amase incidents`.
  - **Files:** `scripts/diagnose-failure.py`, `scripts/generate-agent.sh`, `scripts/status.py`, `scripts/engine_incident.py`, `BACKLOG.md`.
  - **Criteria:** Retrospectives write to `~/.amase/retrospectives.jsonl`; `amase incidents` lists global retrospectives; test gate passes.

- [x] **TASK-65: Purge Machine-Specific GEMINI.md & Standardize on Project AGENTS.md**
  - **Goal:** Remove machine-specific `/home/joao/.gemini/config/GEMINI.md` and standardize all coordinator instructions into repository-level `AGENTS.md` and `.amase/` governance generated by `scripts/init-project.sh`. Ensures AMASE projects are fully autonomous and vendor-neutral across all AI tools (Claude Code, Cursor, OpenCode, Windsurf, Antigravity).
  - **Files:** `scripts/init-project.sh`, `BACKLOG.md`.
  - **Criteria:** `~/.gemini/config/GEMINI.md` removed; `init-project.sh` scaffolds `AGENTS.md` with coordinator protocol; test gate passes.

- [x] **TASK-66: Resilient Worker Heartbeat & Extended Watchdog Stall Threshold (90s)**
  - **Goal:** In `scripts/dispatch-worker.sh`, increase stall threshold from 45s to 90s, use `stdbuf -oL -eL` for unbuffered log streaming, and monitor both local worker log and global OpenCode logs so free-fleet models with high queue/thinking latency are not prematurely killed by the watchdog.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** Watchdog stall threshold extended to 90s; multi-source log delta tracking; test gate passes.

- [x] **TASK-67: Resolve WATCHDOG_STALE_LOG_QUOTA_LOOP and Scout NoneType Fix**
  - **Goal:** In `scripts/dispatch-worker.sh`, track global `opencode.log` byte offset before model execution and eliminate un-offset tail greps that caused rapid-fire 5s kills and an infinite loop resetting `STALL_SECONDS=0`. Guard `scout.py` line 209 against `NoneType` roadmap path.
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/scout.py`, `BACKLOG.md`.
  - **Criteria:** Global log checks use byte offset slices; outer rapid-fire watchdog quota kill removed; scout handles None roadmap cleanly.

- [x] **TASK-68: Worktree Framework Cache Replication, Quota Cache Manager, Local LLM Gating & Cross-Module Type Exhaustiveness**
  - **Goal:** Resolve worktree build resolution errors, model fallback stall loops, and un-gated slow local model execution.
    1. Replicate framework typegen caches (`.wxt`, `.svelte-kit`, `.nuxt`, `.next/types`, `.astro`) from parent repo into ephemeral worktrees in `scripts/run-task.sh`.
    2. Gate local Ollama models behind explicit opt-in (`allow_local_llm: true` or `AMASE_ALLOW_LOCAL_LLM=1`) in `scripts/dispatch-worker.sh` to prevent 120s stalls on slow local models.
    3. Implement `scripts/quota_manager.py` with 15-minute TTL cooldown caching in `~/.amase/cache/quota.json` to skip exhausted model providers instantly across workers.
    4. Mandate cross-module type exhaustiveness verification across the full repo in `personas/builder.md` and `scripts/generate-agent.sh`.
  - **Files:** `scripts/run-task.sh`, `scripts/dispatch-worker.sh`, `scripts/quota_manager.py`, `personas/builder.md`, `scripts/generate-agent.sh`, `.amase/test-gate.sh`, `BACKLOG.md`.
  - **Criteria:** Test gate passes with exit code 0; worktree cache replicates cleanly; quota cooldown skips dead models instantly.

- [x] **TASK-69: Universal Linux Terminal Discovery & Fallback Window Spawning**
  - **Goal:** In `scripts/dispatch-worker.sh`, replace hardcoded `PTYXIS_BIN` with auto-discovery across `ptyxis`, `gnome-terminal`, `kitty`, `alacritty`, `wezterm`, `konsole`, and `xterm` (configurable via `AMASE_TERMINAL`). Implement `--new-window` fallback when `--tab` cannot find an active window, guaranteeing a visible terminal window opens reliably.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** Universal terminal detection; tab-to-window fallback; test gate passes cleanly.

- [x] **TASK-70: Fleet Fallback Reordering, Quota Cache Awareness & Ollama Opt-In in fleet.py**
  - **Goal:** In `scripts/fleet.py` (`query_fleet`), re-order providers to prioritize fast cloud endpoints (Direct Groq and GitHub Models at 1-2s response) ahead of OpenCode CLI, integrate `quota_manager` to skip exhausted free pools, and gate local Ollama behind explicit opt-in (`AMASE_ALLOW_LOCAL_LLM=1`) to eliminate 146%+ CPU lockups on Sentinel/Scout.
  - **Files:** `scripts/fleet.py`, `BACKLOG.md`.
  - **Criteria:** Python compiled cleanly; test gate passes; scout and sentinel execute via fast cloud APIs.

- [x] **TASK-71: Sentinel Flag Argument Parser & Universal Terminal in Settlement**
  - **Goal:** In `scripts/sentinel.py`, use `argparse` for `--repo` and `--base` to eliminate argument collision where passing `--repo` created a literal directory named `--repo`. In `scripts/settle-task.sh`, replace hardcoded Ptyxis with universal terminal auto-discovery (`ptyxis`, `gnome-terminal`, `kitty`, `alacritty`, `wezterm`, `konsole`, `xterm`) and window fallback.
  - **Files:** `scripts/sentinel.py`, `scripts/settle-task.sh`, `BACKLOG.md`.
  - **Criteria:** Sentinel cleanly accepts `--repo <path>` and positional path; settle-task uses universal terminal; test gate passes.

- [x] **TASK-72: Semantic Backlog De-duplication, Empty Settlement Rejection, Transient Retry Backoff & Auto-Cleanup Traps**
  - **Goal:** Address orchestrator friction points:
    1. In `scripts/scout.py`, supply completed task titles to scout prompt and implement token-based Jaccard similarity in `--sanitize` to prevent duplicate slice proposals (e.g. Lever ATS Adapter, QuickFill).
    2. In `scripts/settle-task.sh`, reject settlements where git diff modifies only governance/metadata files (`.amase-*`, `.md`) without modifying functional source/test code.
    3. In `amase`, add 2x retry loop with exponential backoff (30s, 60s) on worker failure before halting to absorb transient 429/503 rate limits.
    4. In `scripts/dispatch-worker.sh` and `amase`, implement `SIGINT`/`SIGTERM` interrupt traps and timeout handlers that cleanly run `abort-task.sh` to prevent orphaned worktrees.
  - **Files:** `scripts/scout.py`, `scripts/settle-task.sh`, `scripts/dispatch-worker.sh`, `amase`, `BACKLOG.md`.
  - **Criteria:** Test gate passes with exit code 0; duplicate tasks rejected; empty settlements blocked; worktrees clean on interrupt.

- [x] **TASK-73: Adaptive Zero-Commit Guardrail (MODEL_ABORT Resolution)**
  - **Goal:** Close the loop on retrospective flight recorder findings: when `MODEL_ABORT` is detected in `~/.amase/retrospectives.jsonl`, dynamically inject adaptive instructions via `scripts/generate-agent.sh` and `personas/builder.md` mandating that workers never exit with zero commits; if a feature already exists, they must add/expand a unit test and commit `test(TASK-XX): verify criteria`.
  - **Files:** `scripts/generate-agent.sh`, `personas/builder.md`, `BACKLOG.md`.
  - **Criteria:** Test gate passes with exit code 0; generate-agent dry-run passes.

- [x] **TASK-74: Failover Error Handoff, Success Win-Rate Tracking & Engine Version in Status**
  - **Goal:**
    1. In `scripts/dispatch-worker.sh`, implement priority error handoff: when model $N$ fails, capture test-gate/compiler errors and inject into model $N+1$'s prompt so subsequent models fix the failure instead of starting blind.
    2. In `scripts/settle-task.sh` and `scripts/diagnose-failure.py`, record `SUCCESS` settlements to flight recorder for positive feedback.
    3. In `scripts/status.py`, report `AMASE Engine: v2.1.0 (<commit>) at <path>` and win-rate statistics (`X settled, Y incidents (Z% win rate)`).
  - **Files:** `scripts/dispatch-worker.sh`, `scripts/settle-task.sh`, `scripts/diagnose-failure.py`, `scripts/status.py`, `BACKLOG.md`.
  - **Criteria:** Test gate passes with exit code 0; amase status displays engine version and win rates; error handoff injected dynamically into next candidate model.

- [x] **TASK-75: Dedicated Python Unit Test Suite (`tests/`) & Test Gate CI Integration**
  - **Goal:** Implement a comprehensive unit test suite in `tests/` covering core AMASE Python modules using standard library `unittest` (zero `pip` dependencies):
    1. `tests/test_quota_manager.py`: Provider normalization, TTL expiration, and cache clearing.
    2. `tests/test_scout.py`: Markdown block parsing, task ID extraction, domain token filtering, and duplicate title detection.
    3. `tests/test_diagnose.py`: Failure log regex classification (`COMPILER_ERROR`, `QUOTA_EXHAUSTED`, `SOCKET_STALL`, `MODEL_ABORT`).
    4. `tests/test_status.py`: Project type detection (Node, Rust, Python, Go, Generic), backlog math, and retrospective win-rate statistics.
    5. Wire `python3 -m unittest discover tests` into `.amase/test-gate.sh`.
  - **Files:** `tests/__init__.py`, `tests/test_quota_manager.py`, `tests/test_scout.py`, `tests/test_diagnose.py`, `tests/test_status.py`, `scripts/scout.py`, `scripts/diagnose-failure.py`, `.amase/test-gate.sh`, `BACKLOG.md`.
  - **Criteria:** 16 unit tests pass in ~1.1s; test gate passes cleanly with exit code 0.

- [x] **TASK-76: Suppress OpenCode Info Logs in Visible Worker Tab**
  - **Goal:** Run OpenCode with `--log-level WARN --print-logs` so stdout only displays essential agent actions, diffs, and warnings rather than noisy framework internals.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** Visible worker terminal displays only meaningful agent progress.

- [x] **TASK-77: Graceful Abort & Tab Cleanup on Fleet Exhaustion**
  - **Goal:** Handle full fleet exhaustion cleanly without SIGKILL/Signal 9 crashes; ensure failed worker terminal tabs close cleanly and prevent zombie tabs on retry.
  - **Files:** `scripts/abort-task.sh`, `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** `abort-task.sh` cleanly terminates worker processes with `pkill -TERM`, removes worktrees and branches without errors.

- [x] **TASK-78: Automated Token Context Injection & Settlement UI Validator**
  - **Goal:** Wire design token injection into `scripts/generate-agent.sh` and add automated UI validation gate in `scripts/settle-task.sh`.
  - **Files:** `scripts/generate-agent.sh`, `scripts/settle-task.sh`, `BACKLOG.md`.
  - **Criteria:** Injected design tokens allow workers to adhere to project UI system; settlement gate verifies UI conformance.

- [x] **TASK-79: WCAG Color Contrast & Form Misalignment Detection in Heuristics**
  - **Goal:** Add WCAG 2.1 AA relative luminance contrast checks (<4.5:1) and form column alignment jitter detection (3-24px) to `scripts/ui_heuristics.js` and `scripts/ui_formatter.py`.
  - **Files:** `scripts/ui_heuristics.js`, `scripts/ui_formatter.py`, `BACKLOG.md`.
  - **Criteria:** Unit tests and self-test pass with contrast and form alignment scoring.

- [x] **TASK-80: Deep Compiler & Typecheck Diagnostic Handoff**
  - **Goal:** Capture granular typecheck/compiler errors (file names, line numbers, error descriptions from `svelte-check` / `tsc` / `cargo check`) in `scripts/dispatch-worker.sh` for model failover handoff.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** Model failover prompt includes the exact error lines from previous attempt.

- [x] **TASK-81: Retrospective Settlement Rejections, Auto-Commit Hygiene & PTY Hangup**
  - **Goal:** Record settlement rejections (`EMPTY_DIFF`, `SETTLEMENT_REJECTED`) in flight recorder; filter out `.amase*` and `telemetry.jsonl` from auto-commits; hangup worker PTY master (`pkill -HUP -t $WORKER_TTY`) on abort; add Invariant 9 enforcing functional source/test edits.
  - **Files:** `scripts/diagnose-failure.py`, `scripts/dispatch-worker.sh`, `scripts/settle-task.sh`, `scripts/abort-task.sh`, `personas/builder.md`, `scripts/generate-agent.sh`, `BACKLOG.md`.
  - **Criteria:** `EMPTY_DIFF` recorded in retrospectives; dead Ptyxis tabs closed via PTY hangup; non-source changes rejected.

- [x] **TASK-82: Milestone Progress Banners & Active Model Heartbeats**
  - **Goal:** Print visible milestone banners in `amase` coordinator terminal (`[▶] STARTING TASK`, `[✓] TASK COMPLETED & SETTLED`), track active model in status, and output 15s heartbeats.
  - **Files:** `amase`, `scripts/dispatch-worker.sh`, `scripts/settle-task.sh`, `BACKLOG.md`.
  - **Criteria:** User sees immediate visual feedback in coordinator terminal on task start, attempt, and settlement.

- [x] **TASK-83: Worker Tab Diff Summary & Clean Tab Auto-Close**
  - **Goal:** Inside visible worker tabs, show git commit message and list of changed files with a 3s countdown before tab auto-closes.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** Worker tab shows clean summary of changes and exits cleanly.

- [x] **TASK-84: Ground Proposed Task Files in Scout Using Repository File Tree**
  - **Goal:** In `scripts/scout.py`, query `git ls-files src/ lib/ entrypoints/` and pass the top existing source files to the Scout prompt to eliminate hallucinated file paths in proposed backlog tasks.
  - **Files:** `scripts/scout.py`, `BACKLOG.md`.
  - **Criteria:** Scout receives real file paths in prompt context; passes test-gate.

- [x] **TASK-85: Fix Scout NoneType Error when Roadmap File is Not Specified or Missing**
  - **Goal:** In `scripts/scout.py`, safely handle `project_roadmap_path` / `roadmap_file` when it is `None` or absent in `discover_tasks()` to prevent `TypeError: stat: path should be string, bytes, os.PathLike or integer, not NoneType`.
  - **Files:** `scripts/scout.py`, `BACKLOG.md`.
  - **Criteria:** `scout.py` safely handles null roadmap without throwing TypeError; passes `.amase/test-gate.sh`.

- [x] **TASK-86: Support `amase run` Alias, `--headless` Flags & Non-Interactive TTY Auto-Detection**
  - **Goal:**
    1. In `amase`, handle `run` subcommand alias and `--headless` / `--no-gui` flags so automated agent sessions do not treat `run` as a target directory path.
    2. In `scripts/dispatch-worker.sh`, auto-detect non-interactive terminals (`[ ! -t 1 ]`) or headless flags and default `USE_GUI_TAB=0` to prevent Ptyxis tab stalls in agent subshells.
    3. Fix `0\n0` arithmetic error in task counter and `jq` boolean parsing for `builder_visible_tab`.
  - **Files:** `amase`, `scripts/dispatch-worker.sh`, `BACKLOG.md`.
  - **Criteria:** `amase run -h` and `amase run --headless -v` exit 0; test gate passes cleanly.

- [x] **TASK-87: Harden Post-Settle Counters, Single-Task (--once) Execution & AGENTS.md Protocol**
  - **Goal:**
    1. In `amase`, eliminate latent `grep -c || echo "$DONE_TASKS"` bug on line 480 and harden all task/pending counters against non-zero exit codes.
    2. Add `--once` / `-1` / `step` CLI flag to `amase` for single-step deterministic execution in agent tool calls.
    3. In `scripts/init-project.sh` and `AGENTS.md`, explicitly declare `amase` as an external CLI binary to prevent LLM tool emulation and enforce `run_command` invocation.
  - **Files:** `amase`, `scripts/init-project.sh`, `AGENTS.md`, `BACKLOG.md`.
  - **Criteria:** `amase --once -h` exits 0; `init-project.sh` dry-run produces updated protocol; test gate passes cleanly.


















- [x] **TASK-ENG-01: Resolve FLEET_EXHAUSTED in dispatch-worker.sh**
  - **Goal:** Fix engine limitation (FLEET_EXHAUSTED) observed in project 'TASK-85': All worker fleet models failed without producing a valid git commit for TASK-85
  - **Files:** scripts/dispatch-worker.sh
  - **Criteria:** python3 -m py_compile scripts/dispatch-worker.sh 2>/dev/null || bash -n scripts/dispatch-worker.sh; .amase/test-gate.sh passes.
- [x] **TASK-UI-01: Show commit summary & 3‑second countdown in visible worker tabs**
  - **Goal:** After a worker finishes its task, display the git commit message and list of changed files, then auto‑close the tab after a 3‑second countdown.
  - **Files:** `scripts/dispatch-worker.sh`, `BACKLOG.md`
  - **Criteria:**  

- [x] **TASK-88: Rewrite `personas/coordinator.md` as Universal AMASE Supervisor Maestro**
  - **Goal:** Replace obsolete Orca references in `personas/coordinator.md` with the modern AMASE Supervisor Maestro persona defining clear routing between User, Project Manager (`pm`), Builder (`amase`), Scout, and Sentinel, strict state-machine transitions (`amase status`, `BACKLOG.md`), context shaping, and zero direct code edits (keep under 3KB).
  - **Files:** `personas/coordinator.md`.
  - **Criteria:** `! grep -qi "orca" personas/coordinator.md` exits 0; file size <= 3072 bytes; `.amase/test-gate.sh` passes with exit code 0.

- [x] **TASK-89: Decouple Core Personas (`builder.md`, `sentinel.md`, `designer.md`, `reviewer.md`) from Specific Projects**
  - **Goal:** Remove hardcoded references to Kandidat, Svelte, WXT, Manifest V3, Chrome Web Store, and ATS platforms from `personas/builder.md`, `personas/sentinel.md`, `personas/designer.md`, and `personas/reviewer.md`, replacing them with universal software engineering invariants (Ponytail/YAGNI, standard library first, `.amase/test-gate.sh`, design token compliance when present, strict language type safety, <3KB each).
  - **Files:** `personas/builder.md`, `personas/sentinel.md`, `personas/designer.md`, `personas/reviewer.md`.
  - **Criteria:** `! grep -rniE "kandidat|svelte|wxt|manifest v3|orca|greenhouse|workday|ashby|chrome web store|simplify|teal|applyall" personas/builder.md personas/sentinel.md personas/designer.md personas/reviewer.md` exits 0; `.amase/test-gate.sh` passes with exit code 0.

- [ ] **TASK-90: Decouple Scout Persona & `scripts/scout.py` from Project-Specific Domain**
  - **Goal:** Rewrite `personas/scout.md` as a generic Autonomous Discovery & Gap Analysis persona (using `.amase/scope.md`, `.amase/discovery.md`, recent commits, and test gaps instead of browser extension/ATS intelligence), and update `scripts/scout.py` `git ls-files` discovery to inspect real repo source files generically without hardcoding `entrypoints/` (keep `tests/test_scout.py` passing).
  - **Files:** `personas/scout.md`, `scripts/scout.py`, `tests/test_scout.py`.
  - **Criteria:** `! grep -rniE "manifest v3|browser extension|entrypoints|greenhouse|workday|ashby|kandidat" personas/scout.md scripts/scout.py` exits 0; `python3 -m unittest discover tests` and `.amase/test-gate.sh` pass with exit code 0.

- [ ] **TASK-91: Implement Project Manager (`pm`) Persona & `scripts/pm.py` Requirement Decomposer**
  - **Goal:** Create `personas/pm.md` (Project Manager persona dedicated to translating user requests and current project status into 1-3 minimal, atomic, verifiable vertical-slice tasks) and `scripts/pm.py` (CLI accepting `--objective`, `--backlog`, `--scope`, `--status`, `--dry-run`, reusing `scripts/fleet.py` and `scripts/scout.py` deduplication/formatting and real `git ls-files`), plus unit tests in `tests/test_pm.py`.
  - **Files:** `personas/pm.md`, `scripts/pm.py`, `tests/test_pm.py`.
  - **Criteria:** `python3 scripts/pm.py --help` exits 0; `python3 -m unittest tests/test_pm.py` passes; `.amase/test-gate.sh` passes with exit code 0.

- [ ] **TASK-92: Wire Project Manager (`amase task`) & Config Routing into CLI and `generate-agent.sh`**
  - **Goal:** Update `amase` so `amase task "<goal>"` invokes `scripts/pm.py` (passing current status/scope/backlog) instead of `scout.py`, register `pm` routing in `.amase/config.json` and `scripts/init-project.sh`, and ensure `scripts/generate-agent.sh` stays compatible with decoupled personas.
  - **Files:** `amase`, `scripts/init-project.sh`, `scripts/generate-agent.sh`, `.amase/config.json`.
  - **Criteria:** `amase --help` documents `task` powered by Project Manager; `.amase/test-gate.sh` passes with exit code 0.
