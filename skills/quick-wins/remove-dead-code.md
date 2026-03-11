---
name: remove-dead-code
description: "Find and remove unused imports, functions, and files. Use when a codebase has accumulated cruft from refactors."
---

# Remove Dead Code

Clean out code that's no longer called or imported.

## Steps

1. **Find unused imports:**
   ```bash
   # Python — use pyflakes or ruff
   python -m pyflakes src/*.py 2>&1 | grep "imported but unused"
   # Or with ruff
   ruff check --select F401 src/
   ```

2. **Find unused functions:**
   ```bash
   # List all function definitions
   grep -rn "^def \|^    def " src/ --include="*.py" | while read line; do
     func=$(echo "$line" | grep -oP 'def \K\w+')
     # Check if called anywhere else
     count=$(grep -rn "\b${func}\b" src/ --include="*.py" | grep -v "^.*:.*def ${func}" | wc -l)
     if [ "$count" -eq 0 ]; then
       echo "UNUSED: $line"
     fi
   done
   ```

3. **Find orphan files** (not imported by anything):
   ```bash
   for f in src/*.py; do
     base=$(basename "$f" .py)
     refs=$(grep -rn "$base" . --include="*.py" --include="*.md" | grep -v "^${f}:" | wc -l)
     if [ "$refs" -eq 0 ]; then
       echo "ORPHAN: $f"
     fi
   done
   ```

4. **Verify before deleting** — check git blame for recent activity:
   ```bash
   git log -1 --format="%ar by %an" -- path/to/suspected_dead.py
   ```
   If last touched >3 months ago and not imported, safe to remove.

5. **Delete with `git rm`** and run tests:
   ```bash
   git rm path/to/dead_code.py
   python -m pytest
   ```

## Anti-patterns

- Don't delete functions called via strings/reflection (e.g., `getattr(obj, func_name)`)
- Don't delete entry points (CLI scripts, cron jobs) just because nothing imports them
- Don't delete test utilities just because production code doesn't import them
