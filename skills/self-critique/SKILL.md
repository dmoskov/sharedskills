---
name: self-critique
description: Post-task self-critique using an independent Gemini reviewer to identify errors or improvements
triggers:
  - "review my work"
  - "critique this"
  - "what did I miss"
  - "self-critique"
  - "audit my changes"
tools_required:
  - Bash
  - Read
---

# Self-Critique Skill

Implements the "confessions" pattern: after completing work, an *independent* model
(Gemini) reviews it, so the author model's blind spots don't go unchallenged. The
reviewer returns structured issues (category, severity, location, suggested fix) and
an overall confidence score.

## When to Use

- After completing a significant code change
- Before committing to version control
- When uncertain about an implementation decision
- As a periodic audit pass over recent work

## Setup (one-time)

1. Get a Gemini API key from https://aistudio.google.com/apikey
2. Store it:
   ```bash
   mkdir -p ~/.config/ai-dev-tools
   echo "your-api-key-here" > ~/.config/ai-dev-tools/gemini_api_key
   chmod 600 ~/.config/ai-dev-tools/gemini_api_key
   ```
   Or set the `GEMINI_API_KEY` environment variable.
3. Optional: override the reviewer model with `GEMINI_MODEL` (pin exact model IDs —
   floating aliases can silently change behavior).

## How to Use

Paths resolve against your ai-dev-tools checkout (see the `AI_DEV_TOOLS_DIR`
convention in [skills/README.md](../README.md)).

After completing a task, run the critique script with a description of what was done:

```bash
python3 "${AI_DEV_TOOLS_DIR:-.}/skills/self-critique/gemini_critique.py" \
  --task "Implemented user authentication" --files src/auth.py src/middleware.py
```

Or for a git-based review of recent changes:

```bash
python3 "${AI_DEV_TOOLS_DIR:-.}/skills/self-critique/gemini_critique.py" \
  --git-diff HEAD~1 --task "Recent changes"
```

Focus the critique on one dimension:

```bash
python3 "${AI_DEV_TOOLS_DIR:-.}/skills/self-critique/gemini_critique.py" \
  --task "Caching layer" --files cache.py --focus security
```

Add `--json` for machine-readable output. The script exits non-zero if any
critical-severity issue is found, so it can gate CI or pre-commit flows.

## Critique Categories

1. **Correctness** - Logic errors, edge cases, off-by-one errors
2. **Security** - Vulnerabilities, injection risks, data exposure
3. **Performance** - Inefficiencies, N+1 queries, memory leaks
4. **Maintainability** - Code clarity, naming, documentation gaps
5. **Completeness** - Missing tests, error handling, validation

## Acting on the Critique

Treat the reviewer as a skeptical colleague, not an oracle:
- **Critical/high issues**: verify each one against the code before fixing — external
  reviewers see plausible-but-wrong issues too. Fix confirmed ones before committing.
- **Medium**: fix or explicitly note why not.
- **Low**: apply judgment; ignore style-only nits.
