# Open-Source Tool Registry: Token Reduction & AST Symbol Indexing

AMASE ingests $0 / open-source utilities to shrink LLM input context by at least 40% before dispatching child workers. All entries are free to use and avoid new runtime dependencies in target projects.

## Selection Criteria

- License: OSS (MIT/Apache/BSD or equivalent).
- Cost: $0 (no paid API keys).
- Effect: reduce inspected source context by >= 40% versus full-file reads.
- Integration: CLI or stdlib-friendly; no `npm install` in target repos.

## Catalog

| Tool | Category | Role | Status | Integration |
| --- | --- | --- | --- | --- |
| Tree-sitter (CLI / py-tree-sitter) | AST outline | Precise symbol extraction (classes, functions, methods, types) across 40+ languages | Optional external | `scripts/outline-ast.py` (stdlib fallback; tree-sitter backend optional) |
| universal-ctags | AST outline | Fast cross-language tag/symbol index | Optional external | `ctags -R --fields=+n -f -` |
| ast-grep (sg) | AST search | Structural code search/refactor without full file dumps | Optional external | `sg --pattern '...' --json` |
| Repomix | Token-minified packing | Packs a repository into one LLM-oriented file with token counts and compression | Optional external | `npx repomix --compress` |
| code2prompt | Context packing | Renders repo to prompt with token accounting and filtering | Optional external | `code2prompt . --output prompt.md` |
| files-to-prompt | Context packing | Concatenates selected files with headers for prompt ingestion | Optional external | `files-to-prompt src/` |
| Gitingest | Context packing | Converts a Git repo into a compact digest for LLMs | Optional external | `gitingest <repo-url>` |
| Selective Context | Prompt compression | Removes low-information tokens/sentences from prompts | Optional external | Python wrapper around `selective_context` |
| LLMLingua / llmlingua-2 | Prompt compression | Compresses long prompts while preserving task-critical content | Optional external | `python -m llmlingua` |
| tiktoken | Token accounting | Measures token counts for budgeting and reduction verification | Optional external | `tiktoken.encoding_for_model(...)` |

## Integrated AMASE Utility

`scripts/outline-ast.py` prints a compact symbol outline for a file or directory (classes, functions, methods, exported types, constants) instead of full source.

```bash
scripts/outline-ast.py src/
scripts/outline-ast.py src/foo.ts --max-depth 2
```

Output includes file line counts and symbol locations, allowing agents to open only relevant ranges.

## Benchmark Method

1. Baseline: token estimate of full source files (`chars / 4`).
2. Candidate: token estimate of `outline-ast.py` output for the same target.
3. Pass: reduction >= 40% with no loss of navigational symbols.

## Verified Status

- `scripts/outline-ast.py`: implemented with Python standard library; compiles and runs in `.amase/test-gate.sh`.
- External tools: optional; install only when a project needs deeper language precision or packing.
