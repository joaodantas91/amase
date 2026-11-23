# AMASE Orchestrator Scope & Governance Boundaries

Core Invariant: **MAXIMUM TOKEN DIET ($0 WORKER FLEET)**.
The orchestrator must remain ultra-lightweight, zero-cost to run on child tasks, and enforce strict boundaries.

## 1. Allowed Scope (Green Zone)
- **Automation Scripts:** Bash scripts in `scripts/` (`run-task.sh`, `dispatch-worker.sh`, `generate-agent.sh`, `settle-task.sh`).
- **Python Personas & Runners:** Python scripts in `scripts/` (`scout.py`, `sentinel.py`, `designer.py`).
- **Prompt Specifications:** Markdown files in `personas/` and `prompts/` (must stay under 3KB per file).
- **LiteLLM Gateway Config:** `config/litellm-config.yaml` (routing free models).
- **Test Gate & Validation:** `.amase/test-gate.sh` and test suites.

## 2. Strictly Forbidden (Red Zone)
- **NO Paid Model Usage for Workers:** Workers must ALWAYS use the $0 Free Fleet (LiteLLM `:4000` -> Groq, NVIDIA NIM, or OpenCode free models). Zero Google AI Studio / Pro quota on child workers.
- **NO Hardcoded Secrets:** Never commit real API keys or tokens. Always use environment variables (`os.environ/...`).
- **NO Context Bloat:** Keep prompts dense and terse (CHISLE / CAVEMAN). Never dump full git histories into prompts.
- **NO Heavy Runtimes:** No heavy frameworks, no bloated node_modules inside orchestrator core. Pure Bash, Python standard library, and lightweight CLIs.
