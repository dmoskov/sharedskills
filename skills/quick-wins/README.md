# Quick Wins Skills

Reusable patterns for common codebase improvements. Each skill is a step-by-step guide that any developer or AI agent can follow.

These are based on patterns we've successfully applied across our projects.

## Skills

| Skill | When to use |
|---|---|
| [reorganize-flat-directories](reorganize-flat-directories.md) | Directory has 20+ files with no grouping |
| [extract-large-functions](extract-large-functions.md) | Functions over 50 lines doing multiple things |
| [add-missing-tests](add-missing-tests.md) | Modules with no test coverage |
| [improve-project-docs](improve-project-docs.md) | CLAUDE.md missing or outdated |
| [remove-dead-code](remove-dead-code.md) | Unused imports, functions, or files accumulating |
| [consolidate-config](consolidate-config.md) | Settings scattered across multiple files |

## How to use

Reference a skill when filing a task:
```
Skill: quick-wins/reorganize-flat-directories
Target: scripts/maintenance/ (currently 100+ files, no subdirectories)
```

Or link from CLAUDE.md:
```markdown
For codebase improvements, see [quick-wins skills](ai-dev-tools/skills/quick-wins/).
```
