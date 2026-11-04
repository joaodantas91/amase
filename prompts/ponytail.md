# DIRECTIVE: PONYTAIL (YAGNI & MINIMALIST ARCHITECTURE)
- Adopt strict YAGNI (You Aren't Gonna Need It).
- Never introduce third-party libraries or external packages if standard library/native features suffice.
- Prefer 10 lines of clean native code over 1 new package dependency in package.json/Cargo.toml.
- Reject premature abstractions, generic wrappers, and factories for single-use routines.
- Produce the absolute minimal code diff required to satisfy the unit test suite.
- If modifying an existing file, keep edits surgical and preserve original formatting and comments.
