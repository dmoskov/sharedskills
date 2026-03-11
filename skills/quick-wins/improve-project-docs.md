---
name: improve-project-docs
description: "Improve project documentation: CLAUDE.md, README, and inline docs. Use when a project lacks clear structure documentation or onboarding guidance."
---

# Improve Project Documentation

Make a project self-explanatory for both humans and AI agents.

## When to use

- CLAUDE.md is missing or outdated
- New contributors (human or AI) can't figure out the project structure
- README doesn't explain how to run, test, or deploy

## Steps

1. **Audit what exists:**
   ```bash
   ls -la README.md CLAUDE.md CONTRIBUTING.md docs/ 2>/dev/null
   # Check staleness
   git log -1 --format="%ar" README.md
   ```

2. **Write or update CLAUDE.md** — this is the AI agent's onboarding doc:
   ```markdown
   # Project Name

   One-line description of what this project does.

   ## Structure
   - `src/` — main application code
   - `tests/` — test suite
   - `scripts/` — operational scripts
   - `config/` — configuration files

   ## Key Commands
   - `make test` — run tests
   - `make lint` — run linter
   - `make deploy` — deploy to production

   ## Architecture Decisions
   - We use X because Y
   - Auth is handled by Z

   ## Gotchas
   - Don't touch file X without also updating Y
   - The Z service requires manual restart after config changes
   ```

3. **Document the directory structure** — show what each top-level directory contains:
   ```bash
   # Generate structure automatically
   find . -maxdepth 2 -type d -not -path './.git*' | sort | \
     sed 's|[^/]*/|  |g'
   ```

4. **Add inline docstrings** to key modules (the ones imported most):
   ```python
   """
   module_name — One line saying what this module does.

   Used by: list the main callers
   Depends on: list external services or configs
   """
   ```

5. **Verify by reading it fresh** — can someone unfamiliar understand the project in 5 minutes?

## Anti-patterns

- Don't document obvious things ("this function returns a string")
- Don't write aspirational docs ("we plan to...") — document what IS
- Don't duplicate code in docs — link to it instead
