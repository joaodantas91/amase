# Discovery & Token Optimization Inbox

Staging area for discovered orchestrator improvements, features, and token-saving ideas.

---

## Active Proposals

- [PROPOSED] **Context Pruner & Diff-Only Prompt Minifier**
  - **Source:** Token Diet Audit
  - **Scope Check:** ALLOWED (`scripts/generate-agent.sh`)
  - **Goal:** Strip non-essential comments and whitespace from injected prompt rules to save 30-40% context window per worker invocation.
  - **Status:** Approved for Backlog

- [PROPOSED] **Open-Source Token Reduction Tool Ingestion (Tree-sitter, Repomix, Selective-Context)**
  - **Source:** User Request
  - **Scope Check:** ALLOWED (`scripts/`, `docs/`)
  - **Goal:** Integrate open-source tools to compress context windows, extract AST symbol maps, and prune prompts before worker dispatch.
  - **Status:** Promoted to Active Backlog (TASK-05)

- [PROPOSED] **Pre-Commit Sandboxing Hook for Worker Worktrees**
  - **Source:** Architecture Review
  - **Scope Check:** ALLOWED (`scripts/run-task.sh`)
  - **Goal:** Inject a `.git/hooks/pre-commit` into worker worktrees that physically blocks commits containing forbidden files or type bypasses before the worker wastes tokens in a loop.
  - **Status:** Approved for Backlog

- [PROPOSED] **Local AST Symbol Extractor (Token-Free Code Map)**
  - **Source:** Token Diet Audit
  - **Scope Check:** ALLOWED (`scripts/`)
  - **Goal:** Provide child agents with a 50-line symbol map instead of making them read 10 full files, cutting token usage by 80%.
  - **Status:** Needs Triage
