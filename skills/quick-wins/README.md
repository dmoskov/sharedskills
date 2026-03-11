# Quick Wins Skills

Reusable patterns for common codebase improvements. Each skill is a step-by-step guide that any developer or AI agent can follow.

Based on patterns we've successfully applied across our projects.

## Skills

| Skill | What it does | Suggested cadence |
|---|---|---|
| [reorganize-flat-directories](reorganize-flat-directories.md) | Group 20+ files into logical subdirectories | Quarterly |
| [extract-large-functions](extract-large-functions.md) | Break 50+ line functions into testable pieces | Weekly |
| [add-missing-tests](add-missing-tests.md) | Add coverage for untested modules | Weekly |
| [improve-project-docs](improve-project-docs.md) | Update CLAUDE.md and README to match reality | Monthly |
| [remove-dead-code](remove-dead-code.md) | Delete unused imports, functions, and files | Bi-weekly |
| [consolidate-config](consolidate-config.md) | Move scattered settings to one source of truth | Monthly |
| [fix-ci-failures](fix-ci-failures.md) | Diagnose and fix CI pipeline failures | As needed |
| [reduce-duplication](reduce-duplication.md) | Extract copy-pasted code into shared functions | Bi-weekly |
| [improve-error-handling](improve-error-handling.md) | Replace silent failures with clear, actionable errors | Monthly |
| [add-type-hints](add-type-hints.md) | Annotate function signatures with types | Monthly |
| [git-hygiene](git-hygiene.md) | Clean stale branches, fix .gitignore, remove large files | Monthly |
| [pin-dependencies](pin-dependencies.md) | Lock versions to prevent surprise breaks | Monthly |
| [security-scan](security-scan.md) | Find hardcoded secrets and insecure defaults | Monthly |

## Scheduling

These work best as recurring hygiene, not one-off cleanups.

**Weekly** (fast, high-signal):
- Extract large functions — they accumulate fast as features ship
- Add missing tests — one untested module per week

**Bi-weekly:**
- Remove dead code — appears after every refactor
- Reduce duplication — catch copy-paste before it spreads

**Monthly:**
- Improve docs, error handling, type hints, git hygiene, deps, config, security
- Each takes 15-30 minutes per project

**Quarterly:**
- Reorganize directories — disruptive, so batch it

**As needed:**
- Fix CI failures — blocking, do immediately

## Integration

Reference from a task:
```
Skill: quick-wins/reduce-duplication
Target: src/api/ (3 files with identical auth header setup)
```

Reference from CLAUDE.md:
```markdown
For codebase improvements, see [quick-wins skills](ai-dev-tools/skills/quick-wins/).
```

For AI agent systems, file as recurring proposed tasks:
```
Skill: quick-wins/remove-dead-code
Target: src/
Schedule: bi-weekly
Auto-approve: yes (no behavior change)
```
