---
name: git-hygiene
description: "Clean up stale branches, fix .gitignore gaps, and remove accidentally committed files."
---

# Git Hygiene

Keep the repo clean so it's easy to navigate and nothing sensitive is exposed.

## Steps

1. **Delete merged branches:**
   ```bash
   # List remote branches merged to main
   git branch -r --merged main | grep -v main | grep -v HEAD
   # Delete them
   git branch -r --merged main | grep -v main | grep -v HEAD | \
     sed 's/origin\///' | xargs -I{} git push origin --delete {}
   # Clean local tracking refs
   git fetch --prune
   ```

2. **Find stale branches** (no commits in 30+ days):
   ```bash
   for branch in $(git branch -r | grep -v HEAD | grep -v main); do
     last_commit=$(git log -1 --format="%ci" "$branch" 2>/dev/null)
     echo "$last_commit $branch"
   done | sort | head -20
   ```

3. **Audit .gitignore gaps:**
   ```bash
   # Files that should probably be ignored
   git ls-files | grep -E "\.env$|\.pyc$|__pycache__|node_modules|\.DS_Store|\.log$"
   # Check what's not tracked but present
   git status --ignored --short
   ```

4. **Remove accidentally committed files** (secrets, build artifacts):
   ```bash
   # Remove from tracking but keep on disk
   git rm --cached path/to/secret.env
   echo "secret.env" >> .gitignore
   git add .gitignore
   git commit -m "Remove accidentally committed secret file"
   ```

   If the file contained secrets, **rotate those secrets immediately** — they're in git history.

5. **Check for large files** that shouldn't be in git:
   ```bash
   git rev-list --objects --all | \
     git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
     awk '/^blob/ {print $3, $4}' | sort -rn | head -20
   ```

## Anti-patterns

- Don't force-push to main to "clean" history — rewrite only on feature branches
- Don't delete branches that have open PRs
- Don't commit `.env` files even with dummy values — use `.env.example` instead
