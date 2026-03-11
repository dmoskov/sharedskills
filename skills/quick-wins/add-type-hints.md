---
name: add-type-hints
description: "Add Python type annotations to untyped functions. Catches bugs at edit time and improves IDE support."
---

# Add Type Hints

Annotate function signatures with types. Start with public APIs and work inward.

## Steps

1. **Find untyped functions:**
   ```bash
   # Functions missing return type
   grep -rn "def .*):$" . --include="*.py" | grep -v "-> " | head -20
   # Or use mypy to find everything
   mypy --disallow-untyped-defs src/ 2>&1 | head -30
   ```

2. **Prioritize:** Type the most-imported modules first (biggest impact):
   ```bash
   for f in src/*.py; do
     base=$(basename "$f" .py)
     count=$(grep -rn "from.*$base import\|import $base" . --include="*.py" | wc -l)
     echo "$count: $f"
   done | sort -rn | head -10
   ```

3. **Add annotations to function signatures:**
   ```python
   # Before
   def process_tasks(tasks, max_retries, timeout):
       results = []
       for task in tasks:
           result = execute(task)
           results.append(result)
       return results

   # After
   def process_tasks(
       tasks: list[dict[str, Any]],
       max_retries: int,
       timeout: float,
   ) -> list[dict[str, Any]]:
       results: list[dict[str, Any]] = []
       for task in tasks:
           result = execute(task)
           results.append(result)
       return results
   ```

4. **Use Optional for nullable values:**
   ```python
   from typing import Optional

   def find_user(user_id: str) -> Optional[User]:
       """Returns None if not found."""
   ```

5. **Validate with mypy:**
   ```bash
   mypy src/module.py --ignore-missing-imports
   ```

## Anti-patterns

- Don't type internal helper functions before public APIs
- Don't use `Any` everywhere — that defeats the purpose
- Don't add types that lie (saying `-> str` when it can return `None`)
