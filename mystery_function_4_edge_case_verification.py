#!/usr/bin/env python3
"""
Mystery Function 4 - Edge Case Verification
Additional testing to ensure the hypothesis is robust across edge cases
"""

from mystery_function_4 import mystery_function_4

def test_edge_cases():
    """Test edge cases to ensure hypothesis holds"""

    print("Mystery Function 4 - Edge Case Verification")
    print("=" * 50)
    print("Hypothesis: Returns True if sum(args) % 7 == 0")
    print("")

    edge_cases = [
        # Empty list test (if allowed)
        # ([]), # This might cause an error, so we'll skip it

        # Large numbers
        ([700]),        # Large multiple of 7
        ([701]),        # Large non-multiple of 7
        ([350, 350]),   # Two large numbers summing to multiple of 7
        ([1000, -993]), # Large positive and negative summing to 7

        # Multiple of 7 with different combinations
        ([1, 1, 1, 1, 1, 1, 1]),           # Seven 1's = 7
        ([2, 2, 3]),                       # Small numbers = 7
        ([100, -93]),                      # = 7
        ([49, 42]),                        # Both multiples of 7, sum = 91 (not divisible by 7)
        ([35, 28]),                        # Both multiples of 7, sum = 63 (divisible by 7)

        # Negative edge cases
        ([-1, -1, -1, -1, -1, -1, -1]),    # Seven -1's = -7
        ([-100, 93]),                      # = -7
        ([-35, -28]),                      # = -63 (divisible by 7)

        # Zero combinations
        ([0]),
        ([0, 0, 0]),
        ([7, 0]),
        ([0, 7]),
        ([0, 0, 7]),

        # Large lists
        ([1] * 7),        # [1, 1, 1, 1, 1, 1, 1] = 7
        ([1] * 8),        # [1, 1, 1, 1, 1, 1, 1, 1] = 8
        ([1] * 14),       # 14 ones = 14 (divisible by 7)
        ([1] * 15),       # 15 ones = 15 (not divisible by 7)

        # Mixed positive and negative
        ([10, -3]),       # = 7
        ([3, -10]),       # = -7
        ([100, -100, 7]), # = 7
        ([50, -50, 0]),   # = 0
    ]

    all_correct = True

    for i, args in enumerate(edge_cases):
        try:
            actual_result = mystery_function_4(args)
            sum_val = sum(args)
            expected_result = (sum_val % 7 == 0)
            is_correct = actual_result == expected_result

            status = "✓" if is_correct else "✗"
            print(f"{status} Test {i+1:2d}: f({args}) = {actual_result}")
            print(f"         Sum = {sum_val}, Expected = {expected_result}")

            if not is_correct:
                all_correct = False
                print(f"         ERROR: Expected {expected_result}, got {actual_result}")

            print()

        except Exception as e:
            print(f"✗ Test {i+1:2d}: f({args}) caused error: {e}")
            all_correct = False
            print()

    return all_correct

def test_mathematical_properties():
    """Test mathematical properties of the divisibility rule"""

    print("Testing Mathematical Properties")
    print("=" * 50)

    # Test that the rule is consistent with modular arithmetic
    test_cases = [
        # If a % 7 == 0 and b % 7 == 0, then (a + b) % 7 == 0
        ([7, 14]),     # 7 % 7 == 0, 14 % 7 == 0, sum = 21 % 7 == 0
        ([21, 28]),    # 21 % 7 == 0, 28 % 7 == 0, sum = 49 % 7 == 0

        # If a % 7 == r and b % 7 == (7-r), then (a + b) % 7 == 0
        ([1, 6]),      # 1 + 6 = 7
        ([2, 5]),      # 2 + 5 = 7
        ([3, 4]),      # 3 + 4 = 7
        ([8, 13]),     # 8 % 7 = 1, 13 % 7 = 6, sum = 21 % 7 == 0
        ([9, 12]),     # 9 % 7 = 2, 12 % 7 = 5, sum = 21 % 7 == 0
        ([10, 11]),    # 10 % 7 = 3, 11 % 7 = 4, sum = 21 % 7 == 0

        # Test with remainders that don't sum to multiple of 7
        ([1, 2]),      # 1 + 2 = 3, not divisible by 7
        ([8, 9]),      # 8 % 7 = 1, 9 % 7 = 2, sum = 17 % 7 = 3
    ]

    all_correct = True
    print("Testing modular arithmetic consistency:")

    for args in test_cases:
        actual_result = mystery_function_4(args)
        sum_val = sum(args)
        expected_result = (sum_val % 7 == 0)
        is_correct = actual_result == expected_result

        remainders = [x % 7 for x in args]
        sum_remainders = sum(remainders) % 7

        status = "✓" if is_correct else "✗"
        print(f"{status} f({args}) = {actual_result}")
        print(f"    Sum = {sum_val}, Sum % 7 = {sum_val % 7}")
        print(f"    Individual remainders: {remainders}, Sum of remainders % 7 = {sum_remainders}")
        print(f"    Expected = {expected_result}")
        print()

        if not is_correct:
            all_correct = False

    return all_correct

if __name__ == "__main__":
    print("Starting comprehensive edge case verification...")
    print()

    # Test edge cases
    edge_cases_pass = test_edge_cases()

    # Test mathematical properties
    math_properties_pass = test_mathematical_properties()

    # Final summary
    print("=" * 60)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 60)

    if edge_cases_pass and math_properties_pass:
        print("✓ ALL TESTS PASSED!")
        print()
        print("CONFIRMED CONCLUSION:")
        print("The mystery_function_4 returns True if and only if")
        print("the sum of its arguments is divisible by 7.")
        print()
        print("Mathematical formula: mystery_function_4(args) = (sum(args) % 7 == 0)")
        print()
        print("This rule is consistent across:")
        print("- Positive and negative numbers")
        print("- Large and small numbers")
        print("- Single elements and multiple elements")
        print("- Zero values")
        print("- All edge cases tested")

    else:
        print("✗ SOME TESTS FAILED!")
        if not edge_cases_pass:
            print("- Edge case tests failed")
        if not math_properties_pass:
            print("- Mathematical property tests failed")
        print("Further investigation needed.")