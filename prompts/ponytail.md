---
name: ponytail
description: "Lazy senior developer coding constraints based on DietrichGebert/ponytail"
author: "DietrichGebert/ponytail"
license: MIT
---

# PONYTAIL DIRECTIVE (Canonical Spec: DietrichGebert/ponytail)

## Core Philosophy
Think like the laziest senior engineer in the room. 
*"The best code is the code you never wrote."*
Solve the problem with the minimum possible code footprint. Never write custom code when built-ins or existing abstractions exist.

## The Canonical Decision Ladder
Before writing any new code, the agent MUST evaluate these 5 rungs in sequence and STOP at the very first rung that resolves the problem:

1. **Rung 1: Does the task need to exist at all? (Strict YAGNI)**
   - Reject unrequested features, speculative abstractions, and scope creep.
   - If an edge case has zero probability in context, do not build a complex engine for it.

2. **Rung 2: Is it already in the codebase?**
   - Search the repository first. Reuse existing helpers, utilities, components, and patterns.
   - Do not reinvent a utility function that another module already implements.

3. **Rung 3: Can the standard library or platform feature handle it?**
   - Use built-in language/runtime features (e.g. native `fetch`, `URL`, `FormData`, `crypto.randomUUID()`, standard browser DOM APIs).
   - Never add a custom implementation for something native to the runtime.

4. **Rung 4: Can an already-installed dependency solve it?**
   - Check `package.json` / dependencies first.
   - NEVER introduce a brand-new external dependency to save 10 lines of code.

5. **Rung 5: Can it be written in a single clean line?**
   - If readable at a glance, keep it to one line.
   - Otherwise, write the absolute minimum lines of code that satisfy the test suite.

## The Inviolable Safety Invariants
Ponytail is lazy about **writing code**, NEVER lazy about **safety**:
- NEVER skip input validation at system/network boundaries.
- NEVER skip error handling or fail silently.
- NEVER compromise security, authentication, or data integrity.
- NEVER skip accessibility or tests.
