---
name: amase-invariants
description: Master autonomous invariants for all child personas (Builder, Sentinel, Scout, Designer).
---
# AMASE Master Invariants
1. CAVEMAN: Zero conversational filler. Evidence-first reporting.
2. PONYTAIL: Standard library first. Minimal diff. Zero redundant packages.
3. CHISLE: Token diet. Targeted reads.
4. STRICT TYPES: Zero 'as any', zero '@ts-ignore'. All code & tests strictly typed.
5. DEFINITION OF DONE: Exit code 0 on `bunx vitest run` & `bun run check`. Clean git commit before sending `worker_done`.
6. PERSONA MODEL QUOTA FENCE:
   - Builder (Large context, tool schemas > 8k tokens): NVIDIA NIM / OpenRouter ($0, 128k context). Never route Builder to Groq free (8k TPM limit).
   - Scout / Classifiers (Micro-tasks < 2k tokens): Groq (sub-second latency, $0).
   - Sentinel (Code audit & diff review): NVIDIA NIM (large diff context, $0).
   - OpenCode Free Community Pool: Fallback only; kill and auto-skip in <1s if quota limit is reached.
7. CONCURRENCY & PARALLEL EXECUTION:
   - Default concurrency is `sequential` (zero-risk, 1 worker at a time).
   - In `parallel` mode (`amase config --set-concurrency parallel`), only tasks with strictly disjoint target file sets execute concurrently in isolated worktrees (`.worktrees/<TASK_ID>`).
   - Upstream provider sharding is mandatory across concurrent workers (Worker 1 -> NVIDIA NIM, Worker 2 -> Local Ollama / OpenCode Beam) to eliminate API 429 rate limits.
   - Settlement is strictly sequential: test-gate -> git merge -> sentinel audit -> prune.
