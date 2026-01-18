#!/usr/bin/env python3
"""
Final Verification Script for Mystery Function 1
This script confirms our identified behavior through comprehensive testing
"""

from mystery_function_test import mystery_function

def verify_function_behavior():
    """Verify all identified behaviors are correct"""
    print("🔍 FINAL VERIFICATION OF MYSTERY FUNCTION 1 BEHAVIOR")
    print("="*60)

    all_tests_passed = True

    # Test 1: Positive numbers -> x²
    print("\n✅ Testing: Positive numbers -> x²")
    positive_tests = [(1, 1), (2, 4), (3, 9), (4, 16), (0.5, 0.25), (1.5, 2.25)]
    for input_val, expected in positive_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f({input_val}) = {result} (expected {expected})")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected {expected})")
            all_tests_passed = False

    # Test 2: Negative numbers -> |x|
    print("\n✅ Testing: Negative numbers -> |x|")
    negative_tests = [(-1, 1), (-2, 2), (-3, 3), (-0.5, 0.5), (-1.5, 1.5)]
    for input_val, expected in negative_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f({input_val}) = {result} (expected {expected})")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected {expected})")
            all_tests_passed = False

    # Test 3: Zero -> 0
    print("\n✅ Testing: Zero -> 0")
    result = mystery_function(0)
    if result == 0:
        print(f"  ✓ f(0) = {result} (expected 0)")
    else:
        print(f"  ✗ f(0) = {result} (expected 0)")
        all_tests_passed = False

    # Test 4: Strings -> len(string)
    print("\n✅ Testing: Strings -> len(string)")
    string_tests = [("", 0), ("a", 1), ("hello", 5), ("python", 6), ("αβγ", 3)]
    for input_val, expected in string_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f('{input_val}') = {result} (expected {expected})")
        else:
            print(f"  ✗ f('{input_val}') = {result} (expected {expected})")
            all_tests_passed = False

    # Test 5: Numeric lists -> sum(list)
    print("\n✅ Testing: Numeric lists -> sum(list)")
    numeric_list_tests = [
        ([], 0),
        ([1], 1),
        ([1, 2, 3], 6),
        ([-1, -2], -3),
        ([1.5, 2.5], 4.0),
        ([0, 0, 0], 0)
    ]
    for input_val, expected in numeric_list_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f({input_val}) = {result} (expected {expected})")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected {expected})")
            all_tests_passed = False

    # Test 6: Mixed/non-numeric lists -> len(list)
    print("\n✅ Testing: Mixed/non-numeric lists -> len(list)")
    mixed_list_tests = [
        (['a', 'b'], 2),
        ([1, 'a'], 2),
        (['hello', 'world'], 2),
        ([True, False], 2),  # Note: bool is numeric in Python, but this tests mixed behavior
        ([1, 2, 'string'], 3)
    ]
    for input_val, expected in mixed_list_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f({input_val}) = {result} (expected {expected})")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected {expected})")
            all_tests_passed = False

    # Test 7: Boolean -> treated as int
    print("\n✅ Testing: Boolean -> treated as int")
    bool_tests = [(True, 1), (False, 0)]  # True²=1, False²=0
    for input_val, expected in bool_tests:
        result = mystery_function(input_val)
        if result == expected:
            print(f"  ✓ f({input_val}) = {result} (expected {expected})")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected {expected})")
            all_tests_passed = False

    # Test 8: Other types -> None
    print("\n✅ Testing: Other types -> None")
    other_tests = [None, {}, {"key": "value"}, set([1, 2, 3]), (1, 2, 3)]
    for input_val in other_tests:
        result = mystery_function(input_val)
        if result is None:
            print(f"  ✓ f({input_val}) = {result} (expected None)")
        else:
            print(f"  ✗ f({input_val}) = {result} (expected None)")
            all_tests_passed = False

    # Summary
    print("\n" + "="*60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! Mystery function behavior correctly identified!")
        print("\n📋 CONFIRMED BEHAVIOR:")
        print("   • Positive numbers: f(x) = x²")
        print("   • Negative numbers: f(x) = |x|")
        print("   • Zero: f(0) = 0")
        print("   • Strings: f(x) = len(x)")
        print("   • Numeric lists: f(x) = sum(x)")
        print("   • Mixed/non-numeric lists: f(x) = len(x)")
        print("   • Boolean: treated as int (True=1, False=0)")
        print("   • Other types: f(x) = None")
        return True
    else:
        print("❌ Some tests failed. Review the results above.")
        return False

def provide_final_answer():
    """Provide the final answer for the evaluation"""
    print("\n" + "="*80)
    print("🎯 FINAL ANSWER: MYSTERY FUNCTION 1 IDENTIFICATION")
    print("="*80)

    print("\nThe mystery function is a POLYMORPHIC FUNCTION with the following behavior:")
    print("\nFunction Definition:")
    print("```python")
    print("def mystery_function(x):")
    print("    if isinstance(x, (int, float)):")
    print("        if x < 0:")
    print("            return -x  # absolute value")
    print("        elif x == 0:")
    print("            return 0")
    print("        else:")
    print("            return x * x  # x squared")
    print("    elif isinstance(x, str):")
    print("        return len(x)")
    print("    elif isinstance(x, list):")
    print("        return sum(x) if all(isinstance(i, (int, float)) for i in x) else len(x)")
    print("    else:")
    print("        return None")
    print("```")

    print("\nMathematical Representation:")
    print("f(x) = {")
    print("    |x|        if x ∈ ℝ and x < 0")
    print("    0          if x = 0")
    print("    x²         if x ∈ ℝ and x > 0")
    print("    len(x)     if x ∈ String")
    print("    Σx         if x ∈ List[ℝ] (all numeric)")
    print("    len(x)     if x ∈ List[Mixed] (contains non-numeric)")
    print("    None       otherwise")
    print("}")

    print("\nKey Characteristics:")
    print("• Type-dependent behavior (polymorphic)")
    print("• Handles numeric, string, list, and other types differently")
    print("• Boolean values treated as integers (True=1, False=0)")
    print("• Lists have dual behavior based on content type")
    print("• Returns None for unsupported types")

if __name__ == "__main__":
    success = verify_function_behavior()
    if success:
        provide_final_answer()