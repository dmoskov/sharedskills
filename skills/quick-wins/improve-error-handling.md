---
name: improve-error-handling
description: "Replace silent failures, bare excepts, and cryptic errors with clear, actionable error handling."
---

# Improve Error Handling

Make errors loud, specific, and actionable.

## When to use

- You see `except: pass` or `except Exception: pass`
- Error messages say "Something went wrong" with no context
- Functions return `None` on failure instead of raising
- Logs show errors but nobody knows what to do about them

## Steps

1. **Find bad error handling patterns:**
   ```bash
   # Bare excepts
   grep -rn "except:" . --include="*.py" | grep -v "except:\s*$"
   # Silent swallowing
   grep -rn "except.*pass" . --include="*.py"
   # Generic catches
   grep -rn "except Exception" . --include="*.py"
   # None returns that hide errors
   grep -rn "return None" . --include="*.py"
   ```

2. **Fix each category:**

   Bare/generic except → catch specific exceptions:
   ```python
   # Before
   try:
       data = json.loads(raw)
   except:
       data = {}

   # After
   try:
       data = json.loads(raw)
   except json.JSONDecodeError as e:
       raise ValueError(f"Invalid JSON in config file: {e}") from e
   ```

   Silent failure → fail loudly:
   ```python
   # Before
   try:
       send_email(user)
   except Exception:
       pass  # silently drops email failures

   # After
   try:
       send_email(user)
   except smtplib.SMTPException as e:
       logger.error(f"Failed to send email to {user.email}: {e}")
       raise  # or re-raise if caller should handle it
   ```

   Cryptic message → actionable message:
   ```python
   # Before
   raise Exception("Failed")

   # After
   raise ConnectionError(
       f"Cannot reach database at {db_host}:{db_port}. "
       f"Check that the DB is running and credentials in {config_path} are correct."
   )
   ```

3. **Add context to re-raised exceptions:**
   ```python
   try:
       result = process_task(task_id)
   except ProcessingError as e:
       raise ProcessingError(f"Task {task_id} failed during processing: {e}") from e
   ```

4. **Run tests** — better error handling often exposes bugs that were silently swallowed.

## Anti-patterns

- Don't catch exceptions just to log and re-raise at every level (pick one level)
- Don't put business logic in except blocks
- Don't use exceptions for control flow (use return values or conditionals)
