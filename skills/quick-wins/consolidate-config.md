---
name: consolidate-config
description: "Consolidate scattered configuration into a single source of truth. Use when settings are spread across env vars, hardcoded values, and multiple config files."
---

# Consolidate Configuration

Move scattered settings into one config file or module.

## When to use

- Same value is hardcoded in 3+ places
- Config is split between env vars, JSON files, and Python constants
- Changing a setting requires editing multiple files

## Steps

1. **Find all configuration sources:**
   ```bash
   # Hardcoded values
   grep -rn "localhost\|:5432\|:8080\|api_key\|timeout" src/ --include="*.py"
   # Env var reads
   grep -rn "os.environ\|os.getenv\|ENV\[" src/ --include="*.py"
   # Config file reads
   grep -rn "open.*config\|load.*json\|yaml.load" src/ --include="*.py"
   ```

2. **Create a single config module:**
   ```python
   # config.py
   import os

   DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/mydb")
   API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
   MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
   ```

3. **Replace all hardcoded values** with config references:
   ```python
   # Before
   r = requests.get(url, timeout=30)
   # After
   from config import API_TIMEOUT
   r = requests.get(url, timeout=API_TIMEOUT)
   ```

4. **Document all settings** in the config file with comments explaining what each does and what valid values look like.

5. **Add a `.env.example`** showing all available settings:
   ```bash
   DATABASE_URL=postgresql://localhost:5432/mydb
   API_TIMEOUT=30  # seconds
   MAX_RETRIES=3
   ```

## Anti-patterns

- Don't create a God Config with 200+ settings — group by domain
- Don't put secrets in config files — use environment variables or secret managers
- Don't make every single value configurable — only things that actually change between environments
