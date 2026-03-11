---
name: reorganize-flat-directories
description: "Reorganize a flat directory with too many files into logical subdirectories. Use when a directory has 20+ files at the same level with no grouping."
---

# Reorganize Flat Directories

Turn a cluttered flat directory into logical subdirectories without breaking imports.

## When to use

- A directory has 20+ files at the same level
- Files have clear thematic grouping (by function, domain, or lifecycle)
- You keep losing files in the noise

## Steps

1. **Audit current structure and dependencies before touching anything:**
   ```bash
   # Count files
   ls -1 target_dir/ | wc -l
   # Find all imports of files in this directory
   grep -rn "from target_dir" . --include="*.py" | head -30
   grep -rn "import target_dir" . --include="*.py" | head -30
   ```

2. **Identify natural groupings** by reading filenames and first docstrings:
   ```bash
   for f in target_dir/*.py; do
     echo "=== $(basename $f) ==="
     head -5 "$f" | grep -E '""".*"""|^#'
   done
   ```
   Common groupings: by domain (auth, data, api), by function (analysis, cleanup, reporting), by lifecycle (setup, runtime, teardown).

3. **Create subdirectories with `__init__.py`:**
   ```bash
   mkdir -p target_dir/{group_a,group_b,group_c}
   touch target_dir/{group_a,group_b,group_c}/__init__.py
   ```

4. **Move files using `git mv`** (preserves history):
   ```bash
   git mv target_dir/file_a.py target_dir/group_a/
   git mv target_dir/file_b.py target_dir/group_a/
   ```

5. **Add re-exports in the original location** for backward compatibility:
   ```python
   # target_dir/file_a.py (keep as thin shim)
   from target_dir.group_a.file_a import *  # backward compat
   ```
   Or if you can update all callers, skip the shim and fix imports directly.

6. **Update all import paths** across the codebase:
   ```bash
   # Find what needs updating
   grep -rn "from target_dir.file_a" . --include="*.py"
   # Sed replace (test first with --dry-run or grep)
   find . -name "*.py" -exec sed -i 's/from target_dir.file_a/from target_dir.group_a.file_a/g' {} +
   ```

7. **Run tests and linting** to catch any broken imports:
   ```bash
   python -m pytest
   python -m py_compile target_dir/group_a/file_a.py
   ```

## Anti-patterns

- Don't create subdirectories with only 1-2 files — that's over-organizing
- Don't rename files during the move — one change at a time
- Don't skip the backward-compat shim if you can't verify all callers
