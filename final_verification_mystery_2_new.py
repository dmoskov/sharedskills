#!/usr/bin/env python3
"""
Final verification of Mystery Function 2 solution
Test edge cases and confirm Hypothesis C: (a + b) > 5
"""

import sys
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_2 import mystery_function

def test_edge_cases():
    """Test additional edge cases to confirm the solution"""

    print("MYSTERY FUNCTION 2 - FINAL VERIFICATION")
    print("=" * 50)
    print("Hypothesis C: mystery_function(a, b) = (a + b) > 5")
    print("=" * 50)

    # Edge cases around the boundary (sum = 5)
    boundary_cases = [
        # Exactly sum = 5 (should be False)
        (5, 0), (0, 5), (1, 4), (4, 1), (2, 3), (3, 2),
        (-1, 6), (6, -1), (-5, 10), (10, -5),

        # Just above sum = 5 (should be True)
        (6, 0), (0, 6), (1, 5), (5, 1), (2, 4), (4, 2),
        (-1, 7), (7, -1), (-4, 10), (10, -4),

        # Just below sum = 5 (should be False)
        (4, 0), (0, 4), (1, 3), (3, 1), (2, 2),
        (-1, 5), (5, -1), (-6, 10), (10, -6),
    ]

    print(f"\nTesting {len(boundary_cases)} boundary cases:")
    all_correct = True

    for a, b in boundary_cases:
        actual_result = mystery_function(a, b)
        expected_result = (a + b) > 5
        sum_val = a + b

        status = "✓" if actual_result == expected_result else "✗"
        if actual_result != expected_result:
            all_correct = False

        print(f"{status} f({a:3}, {b:3}) = {str(actual_result):5} | sum = {sum_val:3} | sum > 5? {expected_result}")

    print(f"\nBoundary test result: {'PASS' if all_correct else 'FAIL'}")

    # Test with larger numbers
    large_number_cases = [
        (100, -95),    # sum = 5, False
        (100, -94),    # sum = 6, True
        (-100, 105),   # sum = 5, False
        (-100, 106),   # sum = 6, True
        (1000, -1000), # sum = 0, False
        (50, 50),      # sum = 100, True
    ]

    print(f"\nTesting {len(large_number_cases)} cases with larger numbers:")
    for a, b in large_number_cases:
        actual_result = mystery_function(a, b)
        expected_result = (a + b) > 5
        sum_val = a + b

        status = "✓" if actual_result == expected_result else "✗"
        if actual_result != expected_result:
            all_correct = False

        print(f"{status} f({a:4}, {b:4}) = {str(actual_result):5} | sum = {sum_val:4} | sum > 5? {expected_result}")

    print(f"\nLarge number test result: {'PASS' if all_correct else 'FAIL'}")

    # Random stress test
    import random
    random.seed(42)  # For reproducibility

    print(f"\nStress testing with 20 random cases:")
    for i in range(20):
        a = random.randint(-100, 100)
        b = random.randint(-100, 100)

        actual_result = mystery_function(a, b)
        expected_result = (a + b) > 5
        sum_val = a + b

        status = "✓" if actual_result == expected_result else "✗"
        if actual_result != expected_result:
            all_correct = False

        print(f"{status} f({a:3}, {b:3}) = {str(actual_result):5} | sum = {sum_val:4} | sum > 5? {expected_result}")

    print(f"\nRandom test result: {'PASS' if all_correct else 'FAIL'}")

    print("\n" + "=" * 50)
    if all_correct:
        print("✓ ALL TESTS PASSED!")
        print("CONFIRMED: Mystery Function 2 implements Hypothesis C")
        print("Formula: mystery_function(a, b) = (a + b) > 5")
    else:
        print("✗ SOME TESTS FAILED!")
        print("The mystery function may not implement Hypothesis C")
    print("=" * 50)

    return all_correct

if __name__ == "__main__":
    test_edge_cases()