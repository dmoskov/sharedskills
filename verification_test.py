#!/usr/bin/env python3
"""
Final verification test for mystery function 0
"""

import sys
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_0 import mystery_function

def verify_square_function():
    """
    Verify that the mystery function is indeed f(x) = x^2
    """
    print("Final Verification: Testing mystery_function(x) = x^2")
    print("=" * 50)

    # Test cases that thoroughly verify x^2 behavior
    test_cases = [
        (0, 0),      # 0^2 = 0
        (1, 1),      # 1^2 = 1
        (2, 4),      # 2^2 = 4
        (3, 9),      # 3^2 = 9
        (4, 16),     # 4^2 = 16
        (-1, 1),     # (-1)^2 = 1
        (-2, 4),     # (-2)^2 = 4
        (-3, 9),     # (-3)^2 = 9
        (0.5, 0.25), # (0.5)^2 = 0.25
        (-0.5, 0.25), # (-0.5)^2 = 0.25
        (1.5, 2.25), # (1.5)^2 = 2.25
        (10, 100),   # 10^2 = 100
    ]

    all_correct = True

    for input_val, expected_output in test_cases:
        actual_output = mystery_function(input_val)
        is_correct = actual_output == expected_output
        all_correct = all_correct and is_correct

        status = "✅" if is_correct else "❌"
        print(f"{status} f({input_val}) = {actual_output}, expected {expected_output}")

    print("-" * 50)

    if all_correct:
        print("✅ VERIFICATION PASSED: Mystery function is confirmed to be f(x) = x^2")
        return True
    else:
        print("❌ VERIFICATION FAILED: Mystery function is NOT f(x) = x^2")
        return False

if __name__ == "__main__":
    verify_square_function()