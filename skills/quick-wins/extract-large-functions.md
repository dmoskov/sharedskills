---
name: extract-large-functions
description: "Break up functions over 50 lines into smaller, testable pieces. Use when a function does multiple distinct things sequentially."
---

# Extract Large Functions

Break monolithic functions into focused, testable units.

## When to use

- Function exceeds ~50 lines
- You can identify 2+ distinct phases (setup, processing, cleanup)
- The function has multiple levels of indentation (nested loops/conditions)
- Hard to write unit tests because the function does too much

## Steps

1. **Find large functions:**
   ```bash
   # Python: find functions over 50 lines
   grep -n "def " target_file.py | while read line; do
     lineno=$(echo "$line" | cut -d: -f1)
     echo "$lineno: $(echo "$line" | cut -d: -f2-)"
   done
   ```

2. **Read the function and identify natural seams.** Look for:
   - Comment blocks that say "Step 1:", "Now we...", "Next..."
   - Variable assignments that create intermediate results
   - Try/except blocks wrapping distinct operations
   - Blank lines separating logical sections

3. **Extract bottom-up** (start with the innermost/simplest piece):
   ```python
   # Before:
   def process_data(raw_data):
       # validate
       if not raw_data: raise ValueError("empty")
       cleaned = [x.strip() for x in raw_data if x]
       # transform
       results = []
       for item in cleaned:
           parsed = json.loads(item)
           results.append(transform(parsed))
       # save
       with open("out.json", "w") as f:
           json.dump(results, f)

   # After:
   def validate_data(raw_data):
       if not raw_data: raise ValueError("empty")
       return [x.strip() for x in raw_data if x]

   def transform_batch(cleaned):
       return [transform(json.loads(item)) for item in cleaned]

   def process_data(raw_data):
       cleaned = validate_data(raw_data)
       results = transform_batch(cleaned)
       with open("out.json", "w") as f:
           json.dump(results, f)
   ```

4. **Keep the original function as the coordinator** — it should read like a table of contents.

5. **Write a test for each extracted function:**
   ```python
   def test_validate_data_empty():
       with pytest.raises(ValueError):
           validate_data([])

   def test_transform_batch():
       result = transform_batch(['{"a": 1}'])
       assert len(result) == 1
   ```

6. **Run existing tests** to verify behavior didn't change.

## Anti-patterns

- Don't extract functions that are only called once AND are trivial (3-5 lines)
- Don't pass 6+ parameters to extracted functions — that's a sign you need a class or data object
- Don't change behavior while extracting — refactor and change are separate steps
