# Quick Wins Skills

Reusable patterns for common codebase improvements. Based on what we've actually done across our projects.

Each skill is a step-by-step guide any developer or AI agent can follow. Run them on a recurring cadence — these work best as regular hygiene, not one-off cleanups.

| Skill | What it does | Cadence |
|---|---|---|
| [extract-large-functions](extract-large-functions.md) | Break 50+ line functions into testable pieces | Weekly |
| [add-missing-tests](add-missing-tests.md) | Add coverage for untested modules | Weekly |
| [test-driven-development](test-driven-development.md) | Write failing tests first, commit, then implement | Per feature |
| [remove-dead-code](remove-dead-code.md) | Delete unused imports, functions, and files | Bi-weekly |
| [reduce-duplication](reduce-duplication.md) | Extract copy-pasted code into shared functions | Bi-weekly |
| [fix-ci-failures](fix-ci-failures.md) | Diagnose and fix CI pipeline failures | As needed |
| [improve-error-handling](improve-error-handling.md) | Replace silent failures with clear, actionable errors | Monthly |
| [improve-project-docs](improve-project-docs.md) | Update CLAUDE.md and README to match reality | Monthly |
| [add-type-hints](add-type-hints.md) | Annotate function signatures with types | Monthly |
| [consolidate-config](consolidate-config.md) | Move scattered settings to one source of truth | Monthly |
| [git-hygiene](git-hygiene.md) | Clean stale branches, fix .gitignore, remove large files | Monthly |
| [pin-dependencies](pin-dependencies.md) | Lock versions to prevent surprise breaks | Monthly |
| [security-scan](security-scan.md) | Find hardcoded secrets and insecure defaults | Monthly |
| [reorganize-flat-directories](reorganize-flat-directories.md) | Group 20+ files into logical subdirectories | Quarterly |

To reference from a task: `Skill: quick-wins/reduce-duplication, Target: src/api/`
