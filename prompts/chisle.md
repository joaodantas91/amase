# DIRECTIVE: CHISLE (TOOL LOG COMPRESSION)
- Strip all ANSI color escape codes before re-feeding CLI logs into context.
- When tests pass: report only "ALL TESTS PASSED: [Total count], exit code 0".
- When tests fail: extract strictly the failing assertion and stack trace lines (maximum 30 lines).
- Never re-inject hundreds of lines of passing test steps into the conversation context.
