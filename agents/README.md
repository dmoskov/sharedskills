# Claude Code Agent Personas

Generic subagent role definitions for Claude Code's Agent tool. Each file defines one
specialist role (frontmatter: `name`, `description`, `tools`; body: responsibilities and
working principles). None of them reference any particular project or infrastructure —
drop them into any codebase.

| Persona | Focus |
|---------|-------|
| api | REST interface design and documentation |
| architecture | System structure and technology decisions |
| code-builder | Core feature implementation |
| data | Schemas, migrations, data integrity |
| debugger | Root-cause analysis and bug fixes |
| designer | UX, design systems, visual consistency |
| devops | CI/CD, deployments, system health |
| documentation | Code docs, guides, user documentation |
| frontend | Modern frontend frameworks and responsive UI |
| integration | Third-party APIs and system connections |
| monitoring | Metrics, anomalies, system observation |
| performance | Bottlenecks and resource optimization |
| refactoring | Restructuring for maintainability |
| requirements | Business needs → technical specifications |
| security | Vulnerabilities, hardening, compliance |
| testing | Test suites, reliability, coverage |

## Installing

Claude Code discovers agents from `.claude/agents/` directories. Symlink or copy the
ones you want:

```bash
# Available in every project (user-level)
mkdir -p ~/.claude/agents
ln -s /path/to/ai-dev-tools/agents/debugger.md ~/.claude/agents/debugger.md

# Or all of them, for one project
mkdir -p /path/to/your-project/.claude/agents
for f in /path/to/ai-dev-tools/agents/*.md; do
  [ "$(basename "$f")" = "README.md" ] && continue
  ln -s "$f" "/path/to/your-project/.claude/agents/$(basename "$f")"
done
```

Claude Code then delegates to them by name via the Agent tool (or you can request one
explicitly: "use the debugger agent to ...").

These role names are also the agent-type vocabulary used by the
[task-decomposition skill](../skills/task-decomposition/) when it recommends which
specialist should execute each subtask.
