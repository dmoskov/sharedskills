#!/usr/bin/env python3
"""
Independent verification script for mystery_function_0
Testing the hypothesis that it implements f(x) = x^2 (square function)
"""

import sys
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_0 import mystery_function

def verify_square_hypothesis():
    """
    Independently verify that the mystery function implements f(x) = x^2
    """
    print("INDEPENDENT VERIFICATION: Testing f(x) = x^2 hypothesis")
    print("=" * 60)

    test_cases = [
        # Edge cases
        0,
        # Small positive and negative integers
        1, -1, 2, -2, 3, -3,
        # Larger values
        10, -10, 25, -25,
        # Decimal values
        0.5, -0.5, 1.2, -1.2, 2.7, -2.7,
        # Special mathematical values
        0.1, -0.1, 0.01, -0.01,
        # Larger test values
        100, -100
    ]

    all_correct = True
    failed_cases = []

    print(f"Testing {len(test_cases)} cases against f(x) = x^2:")
    print()

    for i, x in enumerate(test_cases, 1):
        mystery_result = mystery_function(x)
        expected_result = x * x  # This is f(x) = x^2

        is_correct = abs(mystery_result - expected_result) < 1e-10  # Account for floating point precision

        status = "✅" if is_correct else "❌"
        print(f"Test {i:2d}: f({x:6}) = {mystery_result:10}, expected: {expected_result:10} {status}")

        if not is_correct:
            all_correct = False
            failed_cases.append((x, mystery_result, expected_result))

    print("\n" + "=" * 60)

    if all_correct:
        print("🎉 VERIFICATION COMPLETE: ALL TESTS PASSED!")
        print("The mystery function definitely implements f(x) = x^2 (square function)")
        print("Hypothesis A is CONFIRMED.")
        return True
    else:
        print(f"❌ VERIFICATION FAILED: {len(failed_cases)} test(s) failed")
        print("Failed cases:")
        for x, actual, expected in failed_cases:
            print(f"  f({x}) = {actual}, expected: {expected}")
        return False

if __name__ == "__main__":
    success = verify_square_hypothesis()
    if success:
        print("\nFINAL CONCLUSION: Mystery Function implements Hypothesis A - f(x) = x^2")
    else:
        print("\nFINAL CONCLUSION: Hypothesis A (f(x) = x^2) is REJECTED")