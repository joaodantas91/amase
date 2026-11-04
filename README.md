# Autonomous Multi-Agent Swarm Engine (AMASE) Orchestrator

The decoupled control plane for orchestrating autonomous AI fleets with isolated Git worktrees, automatic provider failover, and token-diet prompt directives.

---

## Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │   Coding Agent (OpenCode / Aider)     │
                      └──────────────────┬────────────────────┘
                                         │ Requests (OpenAI API Format)
                                         ▼
                      ┌───────────────────────────────────────┐
                      │    LiteLLM Proxy (http://localhost:4000)
                      └───────┬──────────────┬──────────────┬─┘
                              │              │              │
           1. Primary (Free)  │              │              │
      ┌───────────────────────┘              │              │
      ▼                                      ▼              ▼
┌──────────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Google AI Studio         │    │ NVIDIA NIM       │    │ Groq            │
│ (Gemini 2.0 Flash)       │    │ (Qwen 2.5 Coder) │    │ (Llama 3.3 70B) │
│ 15 RPM / 1,500 RPD Free  │    │ 1,000 Credits    │    │ Free Tier       │
└──────────────────────────┘    └──────────────────┘    └─────────────────┘
      │ (Fails on 429/Quota)                 ▲
      └──────────────────────────────────────┘
             Auto-fallback in <100ms
```

---

## 1. Quick Setup

### Step 1: Configure Free API Keys
Copy the environment template:
```bash
cp .env.example .env
```
Fill in at least one free API key:
* **Google AI Studio:** [aistudio.google.com](https://aistudio.google.com) (Gemini 2.0 Flash free tier)
* **NVIDIA NIM:** [build.nvidia.com](https://build.nvidia.com) (1,000 free credits for Qwen 2.5 Coder)
* **Groq:** [console.groq.com](https://console.groq.com) (Fast free inference)

### Step 2: Start the Failover Proxy
```bash
./scripts/start-proxy.sh
```
* Sets up a local Python virtual environment (`.venv`) if missing.
* Installs `litellm[proxy]`.
* Starts the gateway on `http://localhost:4000`.

---

## 2. Running an Autonomous Worktree Task

To run an autonomous agent task safely on an isolated branch without polluting `main`:

```bash
./scripts/run-task.sh \
  --repo /home/joao/dev/kandidat \
  --task autofill-popup-trigger \
  --test-cmd "bunx vitest run"
```

### What this does:
1. **Creates an isolated Git worktree** at `.worktrees/<task-id>` on branch `feature/<task-id>`.
2. **Injects AMASE Token Directives:**
   - `CAVEMAN`: Zero conversational pleasantries; terse output only.
   - `PONYTAIL`: Strict YAGNI; standard libraries preferred over npm bloat.
3. **Exports Gateway Configuration:**
   - `OPENAI_BASE_URL="http://localhost:4000/v1"`
   - `OPENAI_MODEL_NAME="coding-fleet"`
4. **Validates Test Gate:** Runs the test runner to ensure reproducible evidence before merging.

---

## 3. Sub-Agent Specification Directory
- Single Source of Truth documentation: `joao-os/40 Projetos/Autonomous Agent Swarm - SSOT.md`
- Prompt directives: `prompts/caveman.md`, `prompts/ponytail.md`, `prompts/chisle.md`
- Configuration: `config/litellm-config.yaml`
