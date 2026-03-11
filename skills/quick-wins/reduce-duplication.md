---
name: reduce-duplication
description: "Find and eliminate copy-pasted code blocks. Use when the same logic appears in 3+ places."
---

# Reduce Duplication

Extract repeated code into shared functions or modules.

## Steps

1. **Find duplicated blocks** (exact or near-exact):
   ```bash
   # Quick: find identical lines appearing in multiple files
   grep -rhn "pattern_you_suspect" . --include="*.py" | sort | uniq -c | sort -rn | head -20
   
   # Better: use a tool
   pip install jscpd  # or use PMD's CPD for Java
   jscpd --min-lines 5 --min-tokens 50 src/
   ```

2. **Categorize what's duplicated:**
   - **Utility logic** (string formatting, date parsing, validation) → extract to `utils.py`
   - **API call patterns** (auth headers, error handling, retries) → extract to a client class
   - **Database patterns** (connection setup, query + close) → extract to a DB helper
   - **Config reading** (same env var read in 5 places) → extract to `config.py`

3. **Extract the shared version:**
   ```python
   # Before (in 4 different files):
   headers = {"Authorization": f"Bearer {os.getenv('API_TOKEN')}"}
   r = requests.get(url, headers=headers, timeout=30)
   if r.status_code != 200:
       raise Exception(f"API error: {r.status_code}")

   # After (in shared client):
   # api_client.py
   def api_get(url):
       headers = {"Authorization": f"Bearer {os.getenv('API_TOKEN')}"}
       r = requests.get(url, headers=headers, timeout=30)
       if r.status_code != 200:
           raise ApiError(f"API error: {r.status_code}")
       return r
   ```

4. **Replace all occurrences**, running tests after each replacement:
   ```bash
   # Find all sites to update
   grep -rn "the duplicated pattern" . --include="*.py"
   # Replace one at a time, test between each
   ```

5. **Verify the count went down:**
   ```bash
   # Should now appear in exactly 1 place (the shared version)
   grep -rn "the pattern" . --include="*.py" | wc -l
   ```

## Anti-patterns

- Don't extract duplication that's only coincidental (same code, different reasons to change)
- Don't create a "god util" with 50 unrelated functions — group by domain
- Don't abstract too early — wait until you see 3+ copies before extracting
