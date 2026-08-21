---
name: task-decomposition
description: Break a large or vague task into file-level Asana subtasks with custom fields from your workspace config
triggers:
  - "decompose this task"
  - "break this down"
  - "task decomposition"
  - "split into subtasks"
tools_required:
  - Bash
  - Read
  - Grep
  - Glob
  - Task
  - TodoWrite
---

# Task Decomposition Skill

Break large, module-level, or vague tasks into concrete file-level subtasks that agents
(or humans) can execute independently. Each subtask targets specific files, has clear
acceptance criteria, and is scoped to 30 min - 2 hr of work.

Subtasks are created as Asana subtasks of the parent task, with custom fields
(execution status, effort, project, task type, validation status) populated from
**your workspace configuration** — no GIDs are hardcoded in this skill.

## Setup (one-time)

1. Install the Asana client from this repo: `cd asana && ./setup.sh`, set `ASANA_ACCESS_TOKEN`
2. Create your workspace config:
   ```bash
   python3 asana/asana_config_loader.py template > ~/.config/ai-dev-tools/asana_config.yaml
   # Fill in your workspace's GIDs, then:
   python3 asana/asana_config_loader.py validate
   ```
   See `asana/asana_config.example.yaml` for a fully annotated example, including how
   to discover the GIDs for your workspace, projects, custom fields, and enum options.
3. To invoke this skill from other projects, symlink it into `~/.claude/skills/` (or a
   project's `.claude/skills/`) and tell it where this repo lives:
   ```bash
   ln -s /path/to/ai-dev-tools/skills/task-decomposition ~/.claude/skills/task-decomposition
   export AI_DEV_TOOLS_DIR=/path/to/ai-dev-tools   # add to your shell profile
   ```
   All `asana/...` paths in this skill resolve against `$AI_DEV_TOOLS_DIR` (falling back
   to the current directory, which works when your session is inside this repo or a
   checkout that vendors it, e.g. as a git submodule).

## When to Use

- A task touches multiple files or modules and is too broad for a single work session
- A task description is vague and needs concrete file targets before execution
- An XL or L effort task needs splitting into S/M subtasks
- A task has failed or timed out repeatedly — recurring failure usually means it's
  too large, not that execution keeps getting unlucky

## Should You Decompose? (pre-flight checks)

Decomposition has a cost — more tasks to track, coordination overhead, context split
across siblings. Before decomposing, check:

- **Already decomposed?** If the task has existing subtasks, work those instead of
  creating a second layer.
- **Is it itself a subtask?** Don't create sub-subtasks; work it directly or revisit
  the parent's decomposition.
- **Already in progress?** Read recent comments/activity — if someone is mid-way
  through, decomposing now fragments their work.
- **Big but not complex?** Some L/XL tasks are just *long* (a mechanical rename, a
  large but uniform migration). Length alone doesn't justify decomposition — only
  multiple independent components do.
- **Actually atomic?** A single-file change or simple bug fix never needs this skill,
  whatever its effort label says.

If unsure, do a dry run first: produce the subtask list (Steps 1-5 of the prompt) and
review it before creating anything in Asana. If the "decomposition" comes out as one
real subtask plus filler, the task didn't need decomposing.

## Input

The user provides one of:
1. An Asana task URL or GID
2. A task description (free text)
3. A feature request or bug report

## Workflow

Follow `prompts/decompose.md` for the full decomposition algorithm.

**Quick summary:**
1. **Load config** - Read your workspace's field/enum GIDs via `asana_config_loader.py dump`
2. **Understand** - Parse the task, identify the target project and repo
3. **Scan** - Find affected files using Grep/Glob, read key files
4. **Map dependencies** - Determine which changes depend on others
5. **Decompose** - Break into 3-8 file-level subtasks with targets and criteria
6. **Create in Asana** - File subtasks with proper custom fields and parent linkage

## Output

3-8 Asana subtasks under the parent task, each with:
- **Title**: `[project] Short action description` (e.g., `[my-backend] Add validation to executor.py`)
- **Files**: Specific file paths listed in the task notes
- **Acceptance Criteria**: Testable conditions in the task notes
- **Custom Fields**: Populated from your config (execution status, effort, project, task type, validation status)

## Constraints

- Each subtask MUST target a specific file or small set of files (max 3)
- Each subtask MUST have <50 line changes expected
- Each subtask MUST be completable in 30 min - 2 hr
- Dependencies MUST form a DAG (no circular dependencies)
- Subtasks MUST be independently verifiable
- Total subtask count: 3-8 (fewer is better)

## Related

- `asana/decomposition.py` — programmatic Synapse-style decomposition algorithm
  (constraint analysis, dependency mapping, granularity optimization) for use in
  automated pipelines rather than interactive sessions
