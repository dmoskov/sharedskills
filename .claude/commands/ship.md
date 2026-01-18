Commit and push all changes in the repository, organizing them into logical commits.

## Instructions

1. Run `git stash list` to note the current stash count (for later comparison)
2. Run `git status` to see all changes (staged, unstaged, and untracked files)
3. Run `git diff` and `git diff --cached` to understand the changes
4. Group related changes into logical commits. Consider grouping by:
   - Feature/functionality (e.g., "Add Codex scaffold support")
   - File type or area (e.g., "Update infrastructure configs")
   - Purpose (e.g., "Fix bug in X", "Refactor Y", "Add tests for Z")
5. For each logical group:
   - Stage the relevant files with `git add`
   - Create a commit with a clear, descriptive message
   - Use conventional commit style when appropriate (feat:, fix:, docs:, refactor:, etc.)
6. After all commits are made, push to the remote branch
7. If on a feature branch, just push. If on main, confirm before pushing.
8. **After push**: Run `git stash list` again - if new stashes appeared, pop them to avoid orphaned work

## Commit Message Format

Each commit should end with:
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Important

- Do NOT combine unrelated changes into a single commit
- Keep commits atomic and focused
- If there are too many unrelated changes, create multiple commits
- Ignore any files that look like secrets or credentials
- Skip files in .gitignore
- **NEVER commit submodule pointer changes** - ignore entries that show `(new commits)` in git status
- If git status shows modified submodules (e.g., `modified: ../claude-code (new commits)`), leave them unstaged

## Stash Protection

Pre-commit hooks and rebase operations can create stashes that accumulate over time, leading to orphaned work. Follow these rules:

1. **Before starting**: Run `git stash list` to note existing stash count
2. **After push completes**: Run `git stash list` again
   - If new stashes were created during the process, investigate and pop them
   - Pre-commit hooks often stash unstaged changes temporarily - these should auto-restore but sometimes don't
3. **If rebase conflicts occur**: After resolving and completing, always check `git stash list`
4. **Warning signs**: Messages like `[INFO] Stashing unstaged files to...` or `[INFO] Restored changes from...` indicate stash activity

If you see stashes were created during shipping:
```bash
git stash list                    # Check what's there
git stash show stash@{0}          # See what's in the latest stash
git stash pop                     # Restore and remove if it's your work
```

**Never leave orphaned stashes** - they represent potentially lost work.

## Post-Deployment Monitoring

After pushing changes, especially to automation/orchestration code:

1. **Verify deployment succeeded** - Check that CI/CD pipelines passed
2. **Monitor for errors** - Check logs for the first few minutes:
   - ECS logs: `aws logs tail /ecs/<log-group> --since 5m`
   - Application logs for errors, warnings, or unexpected behavior
3. **Validate system behavior** - Confirm the system is operating correctly:
   - Check task/job status (e.g., `--status` flags on orchestrators)
   - Verify tasks are progressing as expected
   - Look for stale processes or stuck states
4. **Watch for regressions** - If the change affected:
   - Task execution: verify tasks are being picked up and completed
   - API integrations: confirm external services are responding
   - Scheduled jobs: check they're running on schedule

If issues are found, investigate immediately rather than assuming the deployment was successful.

## Asana Task Tracking

After pushing changes, check if the project has corresponding Asana tasks to mark complete:

1. **Check project CLAUDE.md** for Asana project references (look for "Task Tracking" section)
2. **If Asana MCP is connected**: Use `asana_search_tasks` to find related tasks in the project
3. **Mark tasks complete** and add a comment with the commit hash and summary of changes
4. **If MCP not available**: Note the Asana task URL for manual completion

Projects with Asana tracking:
- `kit/` - Geodesic dome project → Asana project 1211710875848660
