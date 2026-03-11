---
name: pin-dependencies
description: "Pin dependency versions to prevent surprise breaks from upstream updates."
---

# Pin Dependencies

Lock your dependency versions so builds are reproducible.

## Steps

1. **Audit current state:**
   ```bash
   # Python: check for unpinned deps
   grep -v "==" requirements.txt | grep -v "^#" | grep -v "^$"
   # Node: check for loose versions
   cat package.json | python3 -c "import sys,json; deps=json.load(sys.stdin).get('dependencies',{}); [print(f'  {k}: {v}') for k,v in deps.items() if not v.startswith(('=','~'))]"
   ```

2. **Generate pinned versions from what's currently working:**
   ```bash
   # Python
   pip freeze > requirements.lock.txt
   # Node
   npm ci  # uses package-lock.json
   ```

3. **Pin in requirements.txt** (keep both loose and locked):
   ```
   # requirements.txt — minimum versions for development
   requests>=2.28
   boto3>=1.26

   # requirements.lock.txt — exact versions for CI/production
   requests==2.31.0
   boto3==1.34.69
   ```

4. **Set up Dependabot or Renovate** for automated version bump PRs:
   ```yaml
   # .github/dependabot.yml
   version: 2
   updates:
     - package-ecosystem: pip
       directory: "/"
       schedule:
         interval: weekly
   ```

5. **Update deliberately** — when bumping, read the changelog:
   ```bash
   pip install --upgrade requests
   python -m pytest  # verify nothing broke
   pip freeze | grep requests  # note the new version
   ```

## Anti-patterns

- Don't pin to exact patch versions in `requirements.txt` for libraries (use `>=` with upper bound)
- Don't ignore Dependabot PRs forever — merge or dismiss them
- Don't pin development-only tools (linters, formatters) as strictly as production deps
