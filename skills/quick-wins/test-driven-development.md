---
name: test-driven-development
description: "Write failing tests first, commit them, then implement code to pass them. Prevents agents from writing tests that validate their own bugs."
---

# Test-Driven Development

Write the tests before the implementation. Commit them separately. This catches the #1 agent coding failure: writing tests that validate incorrect assumptions.

## Why this matters for AI agents

When an agent writes code and tests together, it unconsciously writes tests that confirm what the code does — not what it *should* do. IEEE research (2026) found agents "generate code that runs cleanly while quietly removing safety checks or introducing subtle logic flaws. The code works. The tests pass. Everything is green. And it is still wrong."

Separating test-writing from implementation breaks this feedback loop.

## Steps

1. **Understand the requirement.** Before writing anything, state what the function should do in plain language:
   ```
   # process_payment(amount, currency) should:
   # - Accept positive amounts only (raise ValueError for <= 0)
   # - Convert currency to USD using current rates
   # - Return a PaymentResult with the USD amount and a transaction ID
   # - Raise PaymentError if the conversion service is unreachable
   ```

2. **Write failing tests FIRST:**
   ```python
   def test_rejects_negative_amount():
       with pytest.raises(ValueError, match="must be positive"):
           process_payment(-10, "EUR")

   def test_converts_to_usd():
       result = process_payment(100, "EUR")
       assert result.currency == "USD"
       assert result.amount > 0

   def test_returns_transaction_id():
       result = process_payment(50, "GBP")
       assert result.transaction_id is not None
       assert len(result.transaction_id) > 0

   def test_raises_on_service_failure(monkeypatch):
       monkeypatch.setattr(conversion_service, "get_rate", lambda *a: raise_timeout())
       with pytest.raises(PaymentError):
           process_payment(100, "EUR")
   ```

3. **Commit the tests before writing any implementation:**
   ```bash
   git add tests/test_payment.py
   git commit -m "Add failing tests for process_payment"
   ```
   This is the critical step. The tests are now locked in and can't be retroactively weakened to match a buggy implementation.

4. **Run the tests — they should ALL FAIL:**
   ```bash
   python -m pytest tests/test_payment.py -v
   # Expected: 4 failed
   ```
   If any test passes before you've written the code, the test is wrong.

5. **Now implement the code to make tests pass:**
   ```bash
   # Write the minimum code that passes all tests
   python -m pytest tests/test_payment.py -v
   # Target: 4 passed
   ```

6. **Commit the implementation separately:**
   ```bash
   git add src/payment.py
   git commit -m "Implement process_payment (all tests passing)"
   ```

## For AI agent workflows

When filing a task that should use TDD:
```
Approach: test-driven
1. Write tests based on the requirements in this task description
2. Commit tests to the branch
3. Implement code to pass the tests
4. Commit implementation separately
Do NOT modify tests after writing implementation.
```

The "do not modify tests" constraint is key. If the agent needs to change a test after implementing, it means either:
- The requirement was ambiguous (update the task description, not the test)
- The agent wrote a wrong test (fix the test, re-commit, THEN re-implement)

## Anti-patterns

- Don't write tests and implementation in the same commit
- Don't write tests that test implementation details (mock internals)
- Don't let the agent "fix" failing tests by weakening assertions
- Don't skip the "all tests should fail" verification step
