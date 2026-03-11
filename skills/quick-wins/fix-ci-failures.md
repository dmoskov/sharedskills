---
name: fix-ci-failures
description: "Diagnose and fix CI pipeline failures. Use when a branch fails CI checks and needs to pass before merging."
---

# Fix CI Failures

Systematically diagnose why CI is failing and fix the root cause.

## Steps

1. **Read the actual error, not just the status:**
   ```bash
   # GitHub Actions
   gh run view <run-id> --log-failed
   # Or check the CI log directly — scroll to the FIRST error, not the last
   ```

2. **Classify the failure:**
   - **Lint/format** — `ruff`, `black`, `eslint` complaints → auto-fixable
   - **Type errors** — `mypy`, `pyright` → usually a missing import or wrong type
   - **Test failure** — a test broke → read the assertion, check if test or code is wrong
   - **Import error** — moved/renamed a file without updating imports
   - **Dependency** — missing package, version conflict
   - **Timeout** — test or build taking too long

3. **Fix by category:**

   Lint/format (auto-fix):
   ```bash
   ruff check --fix .
   black .
   ```

   Import errors (after a refactor):
   ```bash
   # Find what's broken
   python -c "import module_name" 2>&1
   # Search for the old import path
   grep -rn "from old_path" . --include="*.py"
   ```

   Test failures:
   ```bash
   # Run just the failing test with verbose output
   python -m pytest tests/test_specific.py::test_name -v --tb=long
   ```

4. **Run the full CI suite locally before pushing:**
   ```bash
   # Match what CI runs
   ruff check .
   python -m pytest
   ```

5. **If the failure is flaky** (passes sometimes, fails sometimes):
   ```bash
   # Run it 5 times to confirm
   for i in $(seq 1 5); do python -m pytest tests/test_flaky.py -x; done
   ```
   Common causes: timing-dependent tests, shared state between tests, network calls in tests.

## Anti-patterns

- Don't skip/disable the failing test without understanding why it fails
- Don't add `# noqa` or `# type: ignore` without a comment explaining why
- Don't fix the symptom (e.g., catching an exception) when the root cause is wrong logic
