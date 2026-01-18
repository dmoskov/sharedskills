#!/usr/bin/env python3
"""
Final verification test for Mystery Function 2
Testing edge cases to confirm Hypothesis C: sum > 5
"""

import sys
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_2 import mystery_function

def final_verification():
    """Final verification with specific edge cases"""
    print("FINAL VERIFICATION: Mystery Function 2")
    print("="*50)
    print("Testing Hypothesis C: f(a,b) = (a + b) > 5")
    print()

    # Critical edge cases for sum > 5
    edge_cases = [
        # Exactly 5 (should be False)
        (2, 3),    # sum = 5
        (0, 5),    # sum = 5
        (5, 0),    # sum = 5
        (-1, 6),   # sum = 5
        (10, -5),  # sum = 5

        # Just above 5 (should be True)
        (3, 3),    # sum = 6
        (2, 4),    # sum = 6
        (1, 5),    # sum = 6 (corrected from the edge case)
        (0, 6),    # sum = 6
        (-2, 8),   # sum = 6

        # Just below 5 (should be False)
        (2, 2),    # sum = 4
        (1, 3),    # sum = 4
        (0, 4),    # sum = 4
        (-1, 5),   # sum = 4
        (10, -6),  # sum = 4

        # Large positive sums (should be True)
        (10, 10),  # sum = 20
        (100, 1),  # sum = 101

        # Large negative sums (should be False)
        (-10, -10), # sum = -20
        (-100, 0),  # sum = -100

        # Zero sum (should be False)
        (0, 0),     # sum = 0
        (5, -5),    # sum = 0
        (10, -10),  # sum = 0
    ]

    all_correct = True
    for a, b in edge_cases:
        actual = mystery_function(a, b)
        expected = (a + b) > 5
        sum_val = a + b

        status = "✓" if actual == expected else "✗"
        print(f"{status} f({a:3}, {b:3}) = {str(actual):5} | sum = {sum_val:3} | expected = {str(expected):5}")

        if actual != expected:
            all_correct = False

    print()
    if all_correct:
        print("✅ ALL TESTS PASSED!")
        print("🎯 CONFIRMED: Mystery Function 2 implements Hypothesis C")
        print("   The function returns True if and only if (a + b) > 5")
    else:
        print("❌ SOME TESTS FAILED!")
        print("   The hypothesis may be incorrect")

    return all_correct

if __name__ == "__main__":
    success = final_verification()
    print(f"\nFINAL RESULT: {'SUCCESS' if success else 'FAILURE'}")