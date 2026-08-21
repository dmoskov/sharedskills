# Claude Code Skills

Reusable skills for Claude Code, in SKILL.md format.

| Skill | What it does |
|-------|--------------|
| [asana](./asana/) | Manage Asana tasks via direct REST API (fast, reliable alternative to MCP Asana tools). See its [README](./asana/README.md). |
| [task-decomposition](./task-decomposition/) | Break a large or vague task into 3-8 file-level Asana subtasks with custom fields. Workspace-agnostic — all GIDs come from your [YAML config](../asana/asana_config.example.yaml). |
| [rlm](./rlm/) | Recursive Language Model: process documents or codebases too large for one context window by delegating to sub-agents. |
| [quick-wins](./quick-wins/) | A library of step-by-step codebase-hygiene playbooks (dead code removal, missing tests, large-function extraction, ...). See its [README](./quick-wins/README.md). |
| [brand-identity](./brand-identity/) | Create a logo mark + token-based theme ("Asphodel method": one SVG path composed by rotation, one-primary/one-accent CSS variables). |

## Using These Skills in Claude Code

Claude Code discovers skills from `.claude/skills/` directories. Symlink the ones you
want (symlinks keep them updated when you `git pull` this repo):

```bash
# Available in every project (user-level)
mkdir -p ~/.claude/skills
ln -s /path/to/ai-dev-tools/skills/task-decomposition ~/.claude/skills/task-decomposition

# Or just for one project (checked into that repo if you like)
mkdir -p /path/to/your-project/.claude/skills
ln -s /path/to/ai-dev-tools/skills/task-decomposition /path/to/your-project/.claude/skills/task-decomposition
```

Then invoke with `/task-decomposition` (or the skill's name) in a Claude Code session.

### Skills that run scripts from this repo

Some skills (e.g. `task-decomposition`) execute helper scripts that live in this
repository, so they need to know where your checkout is when invoked from another
project. Set once in your shell profile:

```bash
export AI_DEV_TOOLS_DIR=/path/to/ai-dev-tools
```

If unset, those skills assume the current directory is the ai-dev-tools checkout
(which is the case when you work inside this repo, or point commands at a vendored
copy such as a git submodule).

### Setup

Most skills need the Asana client dependencies and authentication — see
[SETUP.md](./SETUP.md). The `task-decomposition` skill additionally needs your
workspace config (`asana_config_loader.py`) — see its [SKILL.md](./task-decomposition/SKILL.md).
