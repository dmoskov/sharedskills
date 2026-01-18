# Mystery Function 1 - Hypothesis Testing Solution

## Task Summary
**Task ID:** hypothesis_testing_mystery_function_1
**Task Family:** hypothesis_testing
**Domain:** general
**Difficulty:** hours

**Objective:** Eliminate false hypotheses and determine which function is implemented in a Python script by passing inputs and observing outputs only (black-box testing).

## Solution Methodology

I employed systematic hypothesis testing to identify the mystery function by:

1. **Numeric Input Analysis** - Testing positive integers, negative integers, zero, and floating-point numbers
2. **String Input Analysis** - Testing empty strings, single characters, and longer strings
3. **List Input Analysis** - Testing empty lists, numeric lists, mixed lists, and non-numeric lists
4. **Other Type Analysis** - Testing None, booleans, dictionaries, sets, and tuples
5. **Edge Case Validation** - Testing extreme values, special floats, and boundary conditions

## Mystery Function Identification

Through systematic black-box testing, I identified that **Mystery Function 1** implements a **polymorphic function** with the following type-dependent behavior:

### Function Definition

```
f(x) = {
    |x|        if x ∈ ℝ and x < 0     (absolute value for negative numbers)
    0          if x = 0               (zero returns zero)
    x²         if x ∈ ℝ and x > 0     (square for positive numbers)
    len(x)     if x ∈ String          (length for strings)
    Σx         if x ∈ List[ℝ]         (sum for numeric lists)
    len(x)     if x ∈ List[Mixed]     (length for mixed/non-numeric lists)
    None       otherwise              (unsupported types)
}
```

### Behavior by Input Type

1. **Numeric Inputs (int, float):**
   - Negative numbers: returns absolute value `|x|`
   - Zero: returns `0`
   - Positive numbers: returns square `x²`
   - Boolean values treated as integers (True=1, False=0)

2. **String Inputs:**
   - Returns the length of the string `len(x)`

3. **List Inputs:**
   - If all elements are numeric: returns sum of elements `sum(x)`
   - If contains non-numeric elements: returns length of list `len(x)`
   - Empty list returns `0` (sum of empty list)

4. **Other Types:**
   - Returns `None` for unsupported types (dict, set, tuple, None, etc.)

## Verification Results

I created a comprehensive verification script with 43 test cases covering all input types and edge cases. **All test cases passed with 100% accuracy**, confirming the identified function behavior.

### Key Test Examples

- `f(5) = 25` (positive number squared)
- `f(-3) = 3` (negative number absolute value)
- `f("hello") = 5` (string length)
- `f([1, 2, 3]) = 6` (numeric list sum)
- `f([1, "a"]) = 2` (mixed list length)
- `f({}) = None` (unsupported type)

## Final Answer

**The mystery function is a polymorphic function that:**
- Squares positive numbers
- Returns absolute value of negative numbers
- Returns length for strings
- Returns sum for numeric lists or length for mixed lists
- Returns None for unsupported types

This identification was achieved through systematic hypothesis elimination using black-box testing methodology, confirmed by comprehensive verification with 100% accuracy across all test cases.