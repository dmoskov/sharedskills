---
name: add-missing-tests
description: "Add test coverage for untested modules. Use when a module has functions with no corresponding test file."
---

# Add Missing Tests

Write focused tests for modules that have zero or minimal test coverage.

## When to use

- A module has no test file at all
- Core logic functions lack edge case coverage
- You're about to refactor and want a safety net first

## Steps

1. **Find untested modules:**
   ```bash
   # List source files without matching test files
   for f in src/*.py; do
     base=$(basename "$f" .py)
     test_file="tests/test_${base}.py"
     if [ ! -f "$test_file" ]; then
       echo "UNTESTED: $f"
     fi
   done
   ```

2. **Prioritize by risk:** Test the files that are imported the most:
   ```bash
   for f in src/*.py; do
     base=$(basename "$f" .py)
     count=$(grep -rn "import.*$base\|from.*$base" . --include="*.py" | wc -l)
     echo "$count imports: $f"
   done | sort -rn | head -10
   ```

3. **Read the module and identify testable functions.** Skip:
   - Functions that only call external APIs (mock those separately)
   - Trivial getters/setters
   - `if __name__ == "__main__"` blocks

4. **Write tests in this order:**
   - **Happy path first** — does it work with normal input?
   - **Edge cases** — empty input, None, single item, max size
   - **Error cases** — does it raise the right exception?

   ```python
   import pytest
   from src.module import function_under_test

   def test_function_happy_path():
       result = function_under_test(valid_input)
       assert result == expected_output

   def test_function_empty_input():
       result = function_under_test([])
       assert result == []

   def test_function_invalid_input():
       with pytest.raises(ValueError):
           function_under_test(None)
   ```

5. **Run and verify:**
   ```bash
   python -m pytest tests/test_module.py -v
   ```

## Anti-patterns

- Don't test implementation details (private methods, internal state)
- Don't write tests that just assert `True` or mock everything
- Don't test framework code (Flask routes, ORM models) — test your logic
- Don't aim for 100% coverage — aim for 100% of important paths
