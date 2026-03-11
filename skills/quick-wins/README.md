# Quick Wins Skills

Reusable patterns for common codebase improvements. Each skill is a step-by-step guide that any developer or AI agent can follow.

These are based on patterns we've successfully applied across our projects.

## Skills

| Skill | When to use | Suggested frequency |
|---|---|---|
| [reorganize-flat-directories](reorganize-flat-directories.md) | Directory has 20+ files with no grouping | Quarterly |
| [extract-large-functions](extract-large-functions.md) | Functions over 50 lines doing multiple things | Weekly |
| [add-missing-tests](add-missing-tests.md) | Modules with no test coverage | Weekly |
| [improve-project-docs](improve-project-docs.md) | CLAUDE.md missing or outdated | Monthly |
| [remove-dead-code](remove-dead-code.md) | Unused imports, functions, or files accumulating | Bi-weekly |
| [consolidate-config](consolidate-config.md) | Settings scattered across multiple files | Monthly |

## Scheduled Maintenance

These skills work best as recurring hygiene, not one-off cleanups. Set up a regular cadence:

### Weekly (low-effort, high-signal)
- **Extract large functions** — Scan for functions >50 lines. These accumulate fast as features ship. One extraction per module per week keeps things manageable.
- **Add missing tests** — Pick the most-imported untested module and add basic coverage. 30 minutes per module.

### Bi-weekly
- **Remove dead code** — Run the unused import/function scan. After any significant refactor, dead code appears. Catching it within 2 weeks means you still remember what it was.

### Monthly
- **Improve project docs** — Re-read CLAUDE.md and README. Do they still match reality? Architecture evolves faster than docs. 15 minutes per project.
- **Consolidate config** — Grep for new hardcoded values that crept in. Developers under time pressure hardcode first and never come back.

### Quarterly
- **Reorganize flat directories** — Count files per directory. Any over 20? Time to group. This is disruptive so do it less often, but don't let it go past a quarter.

### Automation

If you have a task scheduler or proactive system, wire these up:

```bash
# Example cron entries (adjust paths to your project)
# Weekly: find large functions and file tasks
0 9 * * MON  cd /project && python -c "
  import subprocess
  result = subprocess.run(['grep', '-rn', 'def ', 'src/', '--include=*.py'], capture_output=True, text=True)
  # count lines per function, flag >50
"

# Bi-weekly: dead code scan
0 9 1,15 * *  cd /project && python -m pyflakes src/ 2>&1 | grep "imported but unused"

# Monthly: check doc freshness
0 9 1 * *  cd /project && git log -1 --format="%ar" CLAUDE.md README.md
```

Or with Claude Code hooks:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "command": "echo 'Reminder: run quick-wins/extract-large-functions if the changed file has functions >50 lines'"
    }]
  }
}
```

For AI agent systems, file these as recurring proposed tasks with the skill name in the description:
```
Skill: quick-wins/remove-dead-code
Target: src/
Schedule: bi-weekly
Auto-approve: yes (low risk, no behavior change)
```

## How to reference

From a task description:
```
Skill: quick-wins/reorganize-flat-directories
Target: scripts/maintenance/ (currently 100+ files, no subdirectories)
```

From CLAUDE.md:
```markdown
For codebase improvements, see [quick-wins skills](ai-dev-tools/skills/quick-wins/).
```
