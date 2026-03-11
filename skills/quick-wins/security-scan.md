---
name: security-scan
description: "Scan for hardcoded secrets, insecure defaults, and common security mistakes."
---

# Security Scan

Find and fix the low-hanging security issues before they become incidents.

## Steps

1. **Scan for hardcoded secrets:**
   ```bash
   # Common patterns
   grep -rn "password\s*=\s*['\"]" . --include="*.py" --include="*.js" --include="*.ts" | grep -v "test_\|_test\.\|mock\|example\|placeholder"
   grep -rn "api_key\s*=\s*['\"]" . --include="*.py" --include="*.js"
   grep -rn "AKIA[0-9A-Z]" .  # AWS access keys
   grep -rn "sk-[a-zA-Z0-9]" .  # OpenAI/Anthropic keys
   grep -rn "ghp_\|gho_\|github_pat_" .  # GitHub tokens
   
   # Better: use a dedicated tool
   pip install detect-secrets
   detect-secrets scan --all-files
   ```

2. **Check for insecure defaults:**
   ```bash
   # Debug mode in production configs
   grep -rn "DEBUG\s*=\s*True" . --include="*.py"
   # Permissive CORS
   grep -rn "allow_origins.*\*\|CORS.*\*" . --include="*.py"
   # HTTP instead of HTTPS
   grep -rn "http://" . --include="*.py" | grep -v "localhost\|127.0.0.1\|http://"
   ```

3. **Check dependency vulnerabilities:**
   ```bash
   # Python
   pip install safety
   safety check -r requirements.txt
   # Node
   npm audit
   ```

4. **Fix findings:**
   - Secrets → move to environment variables or secret manager
   - Debug flags → make them env-var controlled, default to off
   - Vulnerable deps → upgrade to patched version

5. **Prevent recurrence:**
   - Add `detect-secrets` to CI pre-commit hook
   - Add `.env` and `*.key` to `.gitignore`
   - If secrets were committed, **rotate them immediately**

## Anti-patterns

- Don't just add secrets to `.gitignore` — they're already in git history
- Don't suppress security tool warnings without documenting why
- Don't hardcode "temporary" secrets — there's nothing more permanent
