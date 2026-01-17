# AI Dev Tools - CLAUDE.md

## Universal Instructions
See: ~/Code/CLAUDE.md for universal coding standards

## Project-Specific Instructions

### Project Overview
AI Dev Tools is a collection of tools for AI-assisted development:
- **asana/** - REST API client for Asana task management
- **letta/** - Persistent memory hooks for Claude Code

### Development Guidelines
- Keep tools self-contained with minimal dependencies
- Each tool should work independently
- Document all public APIs
- Include setup guides for each tool

### Tool Structure
Each tool directory should have:
- `README.md` - Quick start and overview
- `SETUP.md` - Detailed setup instructions
- `requirements.txt` - Python dependencies
- Main script(s) with CLI support

### Testing
```bash
# Asana
python3 asana/asana_client.py workspaces  # Requires ASANA_ACCESS_TOKEN

# Letta hooks syntax check
python3 -m py_compile letta/hooks/*.py
python3 -m py_compile letta/hooks/utils/*.py
```

---

# Universal Development Guidelines for Claude
Last Updated: 2025-01-17

## Core Principles

### File Management
- **ALWAYS prefer editing existing files to creating new ones**
- **NEVER proactively create documentation files (*.md) unless explicitly requested**
- **NEVER create new index.html files** - edit existing ones
- Check for existing files before creating anything new
- Maintain existing project structures - don't reorganize without permission

### Version Control
- **NEVER commit or push changes unless explicitly asked**
- **NEVER update git config**
- When asked to commit, include commit message with:
  ```
  > Generated with [Claude Code](https://claude.ai/code)
  
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### Error Handling Philosophy
- **Fail loudly with clear, actionable error messages**
- **Avoid fallback patterns that hide errors**
- Preserve full error context and stack traces
- Don't suppress errors with generic try/catch blocks
- Include specific error details in user-facing messages

### Code Quality
- Follow existing code patterns and conventions in each project
- Check neighboring files for library usage before adding new dependencies
- Use existing utilities and helpers rather than reimplementing
- Run lint and typecheck commands after making changes
- Test changes before marking tasks complete

### Communication Style
- Be concise and direct
- Reference code locations as `file_path:line_number`
- Explain non-trivial bash commands before running them
- Don't add code comments unless requested
- Avoid unnecessary preamble or postamble in responses

## Development Workflow

### Before Making Changes
1. Use Task tool for complex searches across codebases
2. Read existing code to understand conventions
3. Check for existing implementations before creating new ones
4. Look at package.json/requirements.txt for available dependencies

### After Making Changes
1. Run appropriate lint command (npm run lint, ruff, etc.)
2. Run typecheck if available
3. Run tests if test command is known
4. Verify changes work as expected

### Common Commands to Check For
- `npm run lint` / `npm run typecheck`
- `pytest` / `npm test`
- `ruff check` / `black`
- `npm run dev` / `npm start`
- `npm run build`

## Project-Specific Patterns

### Hardware/IoT Projects (ESP32, Arduino)
- Always increment firmware versions
- Include WiFi configuration details
- Document upload procedures
- Note USB device selection requirements

### Database Projects
- Use bastion hosts for RDS access when configured
- Include connection setup in documentation
- Follow query optimization guidelines
- Set statement timeouts for long queries

### UI/Frontend Projects
- Maintain existing design systems
- Follow component patterns from neighboring files
- Don't add unnecessary headers or UI elements
- Keep interfaces clean and intuitive

## Universal Instructions for Subdirectories

When working in any subdirectory:
1. First check for local CLAUDE.md file
2. Follow project-specific instructions if they exist
3. Fall back to these universal guidelines
4. When in doubt, ask for clarification

## Remember

- Each project may have its own CLAUDE.md with specific instructions
- Project-specific instructions override universal ones
- Always read the local CLAUDE.md first
- Use TodoWrite tool to track complex tasks
- Mark todos as completed immediately when done

## Note for Project CLAUDE.md Files

Project-specific CLAUDE.md files should include:
```markdown
## Universal Instructions
See: /Users/moskov/Code/CLAUDE.md for universal coding standards

## Project-Specific Instructions
[Your project-specific content here]
```