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

### `amase config [--show|--mode|--model-tier|--discovery]`

Inspects or toggles project governance settings.

| Flag          | Description                                    |
|---------------|------------------------------------------------|
| `--show`      | Display full config.json                       |
| `--mode`      | Show current mode (`manual` or `autonomous`)   |
| `--model-tier`| Show model tier (`free` or `pro`)              |
| `--discovery` | Show discovery enabled status                  |

```bash
amase config --show
amase config --mode
amase config --model-tier
amase config --discovery
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

Displays the telemetry ledger showing task timestamps, model usage, durations, commit hashes, and $0 cost.

```bash
amase stats                    # Stats for current directory
amase stats ./my-project     # Stats for ./my-project
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