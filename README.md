# Autonomous Multi-Agent Swarm Orchestrator (AMASE)

A unified CLI for orchestrating autonomous AI fleets with isolated Git worktrees, pre-commit sandboxing, and a $0 free model fleet.

---

## Overview

AMASE is an autonomous multi-agent swarm orchestrator that enables safe, isolated task execution via Git worktrees, enforced token-diet constraints, and a bash-free model fleet that runs entirely on free-tier APIs. Key features:

- **Isolated worktree execution**: Each task runs on an isolated branch/worktree, never polluting `main`
- **Pre-commit sandboxing**: Executable hooks block forbidden files (`as any`, `@ts-ignore`) and patterns
- **$0 free model fleet**: All worker tasks use free-tier models via LiteLLM proxy
- **Token-diet governance**: Strict scope boundaries via `.amase/scope.md`
- **Automatic settlement**: Test gate → diff audit → merge → backlog update → worktree prune

---

## CLI Command Reference

### `amase init [dir]`

Scaffolds `.amase` governance files in the target directory:

- `.amase/scope.md` — Project scope & governance boundaries
- `.amase/discovery.md` — Discovery & token optimization inbox
- `.amase/test-gate.sh` — Project-type-aware test runner (Node/Python/Rust/Go)
- `.amase/config.json` — Configuration with `mode`, `model_tier`, `discovery`, `ui.builder_visible_tab`

```bash
amase init                    # Initialize in current directory
amase init ./my-project       # Initialize in ./my-project
```

---

### `amase config [--show|--mode|--concurrency|--set-concurrency <mode>|--set-mode <mode>|--model-tier|--discovery]`

Inspects or toggles project governance settings.

| Flag | Description |
|---|---|
| `--show` | Display full config.json |
| `--mode` | Show current mode (`manual`, `autonomous`, or `interactive`) |
| `--set-mode <mode>` | Set mode (`autonomous` or `interactive`) |
| `--concurrency` | Show current execution concurrency (`sequential` or `parallel`) |
| `--set-concurrency <mode>` | Set concurrency mode (`sequential` or `parallel`) |
| `--model-tier` | Show model tier (`free` or `pro`) |
| `--discovery` | Show discovery enabled status |

```bash
amase config --show
amase config --concurrency                     # Outputs: sequential (default) or parallel
amase config --set-concurrency parallel        # Enable parallel non-conflicting execution
amase config --set-concurrency sequential      # Revert to safe single-worker sequential mode
amase config --set-mode autonomous             # Set autonomous mode
```

---

### `amase task [--dry-run] '<objective>'`

Formulates atomic vertical slice tasks into `BACKLOG.md` from a natural language prompt.

| Flag          | Description                              |
|---------------|------------------------------------------|
| `--dry-run`   | Print the formulated task without appending |

```bash
amase task "Implement popup with settings toggle"
amase task --dry-run "Fix auth middleware bug"
```

---

### `amase stats [dir]`

Displays the telemetry ledger showing task timestamps, persona roles (Builder, Sentinel, Scout), model usage, exact token counts (input/output), durations, commit hashes, and $0 cost.

```bash
amase stats                    # Stats for current directory
amase stats ./my-project     # Stats for ./my-project
```

---

### `amase doctor [dir]`

Performs comprehensive diagnostic health checks across environment prerequisites (Git worktree support, Python 3.10+, Bun/Node runtime, LiteLLM daemon on :4000, OpenCode CLI, Ptyxis terminal, and API keys) with actionable recovery suggestions.

```bash
amase doctor
```

---

### `amase abort <task_id>`

Safely aborts a stalled or failed task, cleanly unmounting the ephemeral Git worktree (`git worktree remove --force`), pruning the branch, and resetting task state in `BACKLOG.md`.

```bash
amase abort TASK-12
```

---

### `amase incidents [--list|--status|--resolve]`

Inspects the global engine incident registry (`~/.amase/engine_issues.jsonl`) recording tool limitations or runtime crashes logged across any project.

```bash
amase incidents                # List pending engine incidents
amase incidents --status all   # List all incidents
```

---

### `amase parallel [--dry-run] [--max-parallel N] [dir]`

Analyzes pending tasks in `BACKLOG.md` for disjoint file targets and executes non-conflicting tasks concurrently in parallel Git worktrees and visible terminal tabs.

```bash
amase parallel --dry-run        # Preview non-conflicting execution batches
amase parallel                  # Run batch in parallel worktrees
amase parallel --max-parallel 3 # Scale to 3 parallel workers
```

---

### `amase ui-check <url> [--viewport WxH] [--json]`

Headless deterministic UI layout and runtime failure validator. Detects viewport overflows, interactive element collisions, broken images, and uncaught console errors, condensing findings into a strict <150-token markdown summary for LLMs (0 image tokens).

```bash
amase ui-check http://localhost:3000                # Check default mobile (375x812)
amase ui-check http://localhost:3000 --viewport 1280x800 # Check desktop
amase ui-check http://localhost:3000 --json         # Full structured JSON telemetry
```

---

### `amase test-wiring`

End-to-end simulation of worktree, AST extraction, git hooks, and settlement in `<2s`. Validates the full pipeline: worktree creation, pre-commit hook enforcement, sentinel audit, and clean teardown.

```bash
amase test-wiring
```

---

### `amase [dir]`

Executes the backlog queue continuously (halts cleanly in manual mode when the queue is empty). In autonomous mode, the loop runs until `BACKLOG.md` is exhausted.

```bash
amase                           # Run loop in current directory
amase ./my-project            # Run loop in ./my-project
```

---

## Configuration (.amase/config.json)

```json
{
  "mode": "manual",
  "model_tier": "free",
  "discovery": {
    "enabled": false,
    "max_slices": 2
  },
  "ui": {
    "builder_visible_tab": true,
    "headless_analyzers": true
  }
}
```

| Key               | Type                        | Description                                                                 |
|-------------------|-----------------------------|-----------------------------------------------------------------------------|
| `mode`            | `string` (`manual`/`autonomous`) | `manual`: halts when BACKLOG.md is empty; `autonomous`: continuous loop     |
| `model_tier`      | `string` (`free`/`pro`)     | `free`: uses $0 free fleet; `pro`: paid model tier                          |
| `discovery.enabled` | `boolean`                 | When `true` and mode=autonomous, scout auto-expands backlog when <3 tasks remain |
| `discovery.max_slices` | `number`                 | Max new tasks to generate per scout expansion                               |
| `ui.builder_visible_tab` | `boolean`               | Controls which tab is visible in the builder UI                             |
| `ui.headless_analyzers` | `boolean`               | Enable headless AST analysis for task routing                               |

---

## Verify & Commit Workflow

After running `amase init`, the pre-commit hook and test gate must pass before committing:

```bash
# 1. Make sure test-gate.sh passes
.amase/test-gate.sh

# 2. Stage and commit
git add .
git commit -m "chore: initialize AMASE governance"

# 3. Verify config is correct
amase config --show
```

The pre-commit hook (injected by `amase test-wiring`) blocks:
- Forbidden files: `package.json`, `.amase/scope.md`
- Forbidden patterns: `as any`, `@ts-ignore`

---

## Quick Start

```bash
# 1. Initialize a new project
amase init ./my-project

# 2. Configure API keys (free fleet only)
cp .env.example .env
# Fill in at least one: Google AI Studio, NVIDIA NIM, or Groq

# 3. Start the Litellm proxy (if not already running)
./scripts/start-proxy.sh

# 4. Add your first task
amase task "Implement settings page with toggle"

# 5. Run the autonomous loop
amase ./my-project
```

---

## Token Efficiency & Mechanical Offloading

AMASE minimizes token consumption by offloading mechanical software engineering operations to deterministic host scripts rather than prompting an LLM:

- **0-Token Operations**: Git worktree branching, environment setup, test gate verification (`test-gate.sh`), forbidden file auditing, and settlement merges run as native host processes (0 tokens consumed). The LLM is invoked only for the pure creative delta: editing code.
- **Local AST Symbol Extraction**: Rather than dumping full source files into the context window, `scripts/outline-ast.py` parses symbols locally and injects only relevant function/class signatures.
- **AST Pre-Filtering**: When tasks target specific modules, `--filter "<keyword>"` restricts the AST symbol map to only those files, eliminating context bloat.
- **Context Hygiene (CHISLE)**: Backlog analysis uses compact slices, and adaptive guardrails restrict file traversal if context bloat was detected in past runs.

---

## Self-Improvement & Engine Feedback Loop

AMASE improves itself cleanly through a two-sided feedback architecture that keeps target projects unpolluted:

1. **Passive Logging in Target Projects**: When executing in an external project (e.g., `kandidat`), AMASE never modifies or edits the orchestrator. If any tool limitation or script error occurs, `scripts/engine_incident.py` registers the incident to `~/.amase/engine_issues.jsonl`.
2. **Orchestrator Ingestion**: When running AMASE within the orchestrator repository itself (`/home/joao/dev/orchestrator`), `scripts/scout.py` reads pending engine incidents and generates `TASK-ENG-XX` backlog tasks.
3. **Deterministic Repair**: The Builder resolves the engine issue, runs the self-test gate, and merges the fix to `main`, instantly updating the tool for all projects.
4. **Dogfooding**: Every feature of AMASE (Tasks 01 through 41) has been developed, gated, audited by Sentinel, and settled using AMASE itself.

---

## Internal Script Reference (`scripts/`)

AMASE is powered by specialized host-side scripts that perform deterministic software engineering tasks at 0 LLM tokens:

### 1. Worktree & Lifecycle Orchestration
- **`init-project.sh`**: Scaffolds `.amase/` governance (`scope.md`, `discovery.md`, `config.json`, `test-gate.sh`) in any target project.
- **`run-task.sh`**: Creates an ephemeral Git worktree (`.worktrees/TASK-XX`), checks out the feature branch, and propagates environment secrets safely.
- **`dispatch-worker.sh`**: Launches the worker in a visible terminal tab (Ptyxis), monitors execution with a sub-second watchdog (<1s quota failover), and manages multi-model fleet rotation.
- **`settle-task.sh`**: Executes deterministic one-click settlement: runs targeted fast tests, full test gate, audits git diff for forbidden patterns, merges to `main`, updates `BACKLOG.md`, records telemetry, and cleanly prunes the worktree.
- **`abort-task.sh`**: Safely tears down failed or stalled tasks, unmounting worktrees (`git worktree remove --force`), pruning branches, and resetting task state.
- **`parallel_dispatcher.py`**: Identifies disjoint file sets between pending backlog items and orchestrates concurrent worker execution across parallel Git worktrees (`amase parallel`).

### 2. Context & AST Extraction (Token Diet)
- **`outline-ast.py`**: Parses codebase AST locally on the host machine to extract class, function, and export signatures without dumping full files into context. Supports `--filter "<keyword>"` for task-targeted symbol pruning.
- **`generate-agent.sh`**: Assembles the dynamic prompt envelope for child workers, combining scope boundaries, filtered AST symbols, and adaptive learned guardrails.

### 3. Multi-Persona Swarm Agents
- **`scout.py`**: Autonomous discovery persona querying LiteLLM free pools to discover the next vertical slices and ingesting external engine incidents when running on the orchestrator.
- **`sentinel.py`**: Post-merge security and invariant auditor inspecting git commits for vulnerabilities, data loss risks, and anti-patterns.
- **`designer.py`**: UI/UX design intelligence auditor inspecting visual frontend components and design systems.
- **`fleet.py`**: Free-tier LiteLLM proxy router and fallback engine managing free model pools ($0 cost).

### 4. Diagnostics, Incidents & Telemetry
- **`doctor.py`**: System health check verifying Git worktree support, Python, runtime environments, LiteLLM daemon on `:4000`, OpenCode CLI, and API keys.
- **`engine_incident.py`**: Central flight recorder logging tool bugs across any target project to `~/.amase/engine_issues.jsonl` and formatting self-healing backlog tasks for the orchestrator.
- **`diagnose-failure.py`**: Retrospective analyzer classifying failed worker runs into machine-readable signatures (`CONTEXT_BLOAT`, `COMPILER_ERROR`, `SOCKET_STALL`, `QUOTA_EXHAUSTED`).
- **`extract_tokens.py`**: Extracts exact LLM token counts from OpenCode's SQLite database (`~/.local/share/opencode/opencode.db`) with fallback duration heuristics.
- **`telemetry.py`**: Multi-persona telemetry logger appending standardized execution records to `.amase/telemetry.jsonl`.
- **`stats.py`**: Formats and prints real-time multi-persona terminal activity logs and role breakdown summaries (`amase stats`).

### 5. Deterministic UI & Visual Validation (0-Token Heuristics)
- **`ui_heuristics.js`**: In-browser DOM evaluator running headlessly to detect horizontal viewport overflows, interactive collisions, and tiny click targets (0 image tokens).
- **`ui_network_audit.py`**: Captures failed network responses (404/500), broken `<img>` assets, and unhandled browser console errors.
- **`ui_formatter.py`**: CHISLE token condenser compiling layout and network findings into a strict <150-token markdown diagnostic.
- **`ui_validator.py`**: Orchestrates headless inspections into the standalone CLI `amase ui-check <url>`.


